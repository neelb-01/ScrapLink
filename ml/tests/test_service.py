import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from scraplink_ml.app import create_app
from scraplink_ml.labels import METALS, NAMES, OTHER, PROMPTS
from scraplink_ml.model import suggest


class FixedScorer:
    name = "fixed"

    def __init__(self, scores: dict[str, float]):
        self._scores = scores

    def scores(self, image):
        return self._scores


def jpeg(colour=(180, 100, 58)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), colour).save(buffer, "JPEG")
    return buffer.getvalue()


def spread(**overrides: float) -> dict[str, float]:
    rest = (1 - sum(overrides.values())) / (len(PROMPTS) - len(overrides))
    return {code: overrides.get(code, rest) for code in PROMPTS}


def test_contract_shape_matches_backend_expectations():
    client = TestClient(create_app(FixedScorer(spread(copper=0.82))))
    body = client.post("/classify", files={"image": ("lot.jpg", jpeg(), "image/jpeg")}).json()
    assert body["material_code"] == "copper"
    assert body["grade"] is None  # this scorer offers no grade
    assert body["grade_confidence"] is None
    assert body["confidence"] == 0.82
    assert body["looks_like_waste"] is True
    assert set(body["scores"]) == set(PROMPTS)


def test_grade_comes_with_its_own_confidence():
    result = suggest(spread(copper=0.8), {"A": 0.2, "B": 0.7, "C": 0.1})
    assert (result["grade"], result["grade_confidence"]) == ("B", 0.7)


def test_scorer_that_assesses_grades_is_used():
    class Grading(FixedScorer):
        def assess(self, image):
            return self._scores, {"A": 0.9, "B": 0.05, "C": 0.05}

    client = TestClient(create_app(Grading(spread(copper=0.82))))
    body = client.post("/classify", files={"image": ("lot.jpg", jpeg(), "image/jpeg")}).json()
    assert (body["grade"], body["grade_confidence"]) == ("A", 0.9)


def test_non_waste_photo_returns_best_material_with_low_confidence():
    result = suggest(spread(**{OTHER: 0.9, "aluminium": 0.04}))
    assert result["material_code"] == "aluminium"
    assert result["confidence"] == 0.04  # far below the backend's 0.75 prefill threshold
    assert result["looks_like_waste"] is False


def test_rejects_non_images():
    client = TestClient(create_app(FixedScorer(spread(copper=0.5))))
    response = client.post("/classify", files={"image": ("x.jpg", b"not an image", "image/jpeg")})
    assert response.status_code == 422


def test_every_backend_material_has_prompts_and_a_grade_name():
    assert set(METALS) == {"copper", "brass", "aluminium", "steel_hms", "cast_iron"}
    assert {"glass_cullet", "textile_waste", "organic_waste"} <= set(PROMPTS)
    assert set(NAMES) == set(PROMPTS) - {OTHER}


@pytest.mark.model
@pytest.mark.skipif(not os.environ.get("RUN_MODEL_TESTS"), reason="set RUN_MODEL_TESTS=1")
def test_real_model_returns_a_probability_distribution():
    client = TestClient(create_app())
    body = client.post("/classify", files={"image": ("lot.jpg", jpeg(), "image/jpeg")}).json()
    assert body["material_code"] in PROMPTS
    assert body["grade"] in ("A", "B", "C")
    assert abs(sum(body["scores"].values()) - 1) < 1e-3
