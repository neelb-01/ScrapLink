"""The training pipeline end to end, with a stand-in for CLIP so no weights are downloaded."""

import csv
import io
import math
import random

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageStat

from scraplink_ml.app import create_app
from scraplink_ml.labels import OTHER
from scraplink_ml.model import ProbeScorer, load_image, suggest
from scraplink_ml.probe import Probe
from scraplink_ml.train import Example, evaluate, group_split, run, suggest_threshold

COLOURS = {"copper": (200, 70, 40), "aluminium": (60, 200, 70), "pet_bottles": (50, 70, 210)}


class ColourEmbedder:
    """Features from a photo's average colour: separable, like CLIP features of distinct metals."""

    name = "colour-test"

    def image(self, image: Image.Image) -> list[float]:
        mean = ImageStat.Stat(image).mean
        norm = math.sqrt(sum(v * v for v in mean)) or 1.0
        return [v / norm for v in mean]


def jpeg(colour, rng: random.Random | None = None) -> bytes:
    if rng:
        colour = tuple(max(0, min(255, c + rng.randint(-15, 15))) for c in colour)
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), colour).save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.fixture
def dataset(tmp_path):
    """What export-training writes: 4 sellers x 3 materials x 3 photos."""
    rng = random.Random(1)
    data = tmp_path / "data"
    rows = []
    for seller in range(4):
        for code, colour in COLOURS.items():
            (data / code).mkdir(parents=True, exist_ok=True)
            for n in range(3):
                path = f"{code}/s{seller}-{n}.jpg"
                (data / path).write_bytes(jpeg(colour, rng))
                rows.append({"path": path, "material_code": code, "group": f"seller-{seller}"})
    with (data / "labels.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["path", "material_code", "group"])
        writer.writeheader()
        writer.writerows(rows)
    return data


def test_trains_reports_and_saves_a_probe(dataset, tmp_path):
    out = tmp_path / "models" / "probe.json"
    report = run(dataset, out, ColourEmbedder(), log=lambda _: None)

    assert report["split_by_seller"] is True
    assert report["held_out"]["accuracy"] == 1.0
    assert report["suggested_threshold"] is not None
    assert "zero_shot_baseline" not in report  # the stand-in has no text side
    probe = Probe.load(out)
    assert probe.classes == ["aluminium", "copper", "pet_bottles"]
    assert probe.evaluation["trained_on"] == {"aluminium": 12, "copper": 12, "pet_bottles": 12}
    assert "ML_CLASSIFICATION_CONFIDENCE_THRESHOLD" in out.with_suffix(".report.txt").read_text()


def test_service_serves_the_trained_probe(dataset, tmp_path):
    out = tmp_path / "probe.json"
    run(dataset, out, ColourEmbedder(), log=lambda _: None)
    scorer = ProbeScorer(Probe.load(out), ColourEmbedder())

    client = TestClient(create_app(scorer))
    body = client.post("/classify", files={"image": ("lot.jpg", jpeg((205, 75, 45)), "image/jpeg")})
    assert body.status_code == 200
    assert body.json()["material_code"] == "copper"
    assert body.json()["confidence"] > 0.75
    assert body.json()["model"].startswith("colour-test+probe(")


def test_negatives_teach_it_to_doubt_photos_that_are_not_scrap(dataset, tmp_path):
    negatives = tmp_path / "negatives"
    negatives.mkdir()
    rng = random.Random(2)
    for n in range(8):
        (negatives / f"n{n}.jpg").write_bytes(jpeg((220, 220, 60), rng))

    out = tmp_path / "probe.json"
    run(dataset, out, ColourEmbedder(), negatives=negatives, log=lambda _: None)
    probe = Probe.load(out)
    assert OTHER in probe.classes

    scores = ProbeScorer(probe, ColourEmbedder()).scores(load_image(jpeg((225, 215, 55))))
    result = suggest(scores)
    assert result["material_code"] != OTHER  # the contract always names a material...
    assert result["confidence"] < 0.5  # ...but with too little confidence to prefill
    assert result["looks_like_scrap_metal"] is False


def test_a_sellers_photos_stay_on_one_side_of_the_split():
    examples = [Example(None, "copper", f"seller-{i % 5}") for i in range(40)]
    train, test, grouped = group_split(examples, 0.25, seed=3)
    assert grouped
    assert {examples[i].group for i in train}.isdisjoint({examples[i].group for i in test})
    assert train and test

    one_seller = [Example(None, "copper", "only") for _ in range(8)]
    train, test, grouped = group_split(one_seller, 0.25, seed=3)
    assert grouped is False
    assert len(test) == 2 and len(train) == 6


def test_threshold_is_the_lowest_one_whose_prefills_are_right_often_enough():
    scores = [
        {"copper": 0.95, "brass": 0.05},  # right, confident
        {"copper": 0.9, "brass": 0.1},  # right, confident
        {"copper": 0.72, "brass": 0.28},  # wrong, middling confidence
        {"copper": 0.4, "brass": 0.6},  # right, unsure
    ]
    result = evaluate(scores, ["copper", "copper", "brass", "brass"])
    assert result["accuracy"] == 0.75
    assert result["confusion"]["brass"] == {"copper": 1, "brass": 1}
    assert suggest_threshold(result["thresholds"], 0.95) == 0.75  # 0.7 lets the wrong one in


def test_probe_refuses_features_from_a_different_model():
    probe = Probe(["a", "b"], [[1.0], [0.0]], [0.0, 0.0], "openai/clip-vit-base-patch32", "now")
    with pytest.raises(ValueError, match="trained on"):
        ProbeScorer(probe, ColourEmbedder())
