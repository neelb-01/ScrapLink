import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from scraplink_ml.app import create_app
from scraplink_ml.labels import METALS, OTHER, PROMPTS
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
    assert body["grade"] is None
    assert body["confidence"] == 0.82
    assert body["looks_like_scrap_metal"] is True
    assert set(body["scores"]) == set(PROMPTS)


def test_non_metal_photo_returns_best_metal_with_low_confidence():
    result = suggest(spread(**{OTHER: 0.9, "aluminium": 0.04}))
    assert result["material_code"] == "aluminium"
    assert result["confidence"] == 0.04  # far below the backend's 0.75 prefill threshold
    assert result["looks_like_scrap_metal"] is False


def test_rejects_non_images():
    client = TestClient(create_app(FixedScorer(spread(copper=0.5))))
    response = client.post("/classify", files={"image": ("x.jpg", b"not an image", "image/jpeg")})
    assert response.status_code == 422


def test_every_backend_material_has_prompts():
    assert set(METALS) == {"copper", "brass", "aluminium", "steel_hms", "cast_iron"}


@pytest.mark.model
@pytest.mark.skipif(not os.environ.get("RUN_MODEL_TESTS"), reason="set RUN_MODEL_TESTS=1")
def test_real_model_returns_a_probability_distribution():
    client = TestClient(create_app())
    body = client.post("/classify", files={"image": ("lot.jpg", jpeg(), "image/jpeg")}).json()
    assert body["material_code"] in METALS
    assert abs(sum(body["scores"].values()) - 1) < 1e-3
