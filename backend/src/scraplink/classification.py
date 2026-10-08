"""Client for the separate ML inference service.

The model only ever *suggests*. Below the confidence threshold the suggestion is not
prefilled, and in every case the seller confirms category and grade before a price exists.
If the service is down or unconfigured, capture carries on with manual selection.

Service contract — POST {ML_SERVICE_URL}/classify, multipart field "image":
    200 {"material_code": "copper", "confidence": 0.0-1.0,
         "grade": "A" | null, "grade_confidence": 0.0-1.0 | null}
"""

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Suggestion:
    material_code: str
    grade: str | None
    confidence: float
    grade_confidence: float | None = None


class Classifier(Protocol):
    def classify(self, image: bytes, content_type: str) -> Suggestion | None: ...


class NullClassifier:
    def classify(self, image: bytes, content_type: str) -> Suggestion | None:
        return None


class HttpClassifier:
    def __init__(self, base_url: str, timeout_seconds: float = 5.0):
        self.url = base_url.rstrip("/") + "/classify"
        # One pooled client: building a client per call costs ~0.3 s (TLS setup) on Windows.
        self._http = httpx.Client(timeout=timeout_seconds)

    def classify(self, image: bytes, content_type: str) -> Suggestion | None:
        try:
            response = self._http.post(self.url, files={"image": ("lot", image, content_type)})
            response.raise_for_status()
            body = response.json()
            grade = body.get("grade")
            grade = grade if grade in ("A", "B", "C") else None
            grade_confidence = body.get("grade_confidence")
            return Suggestion(
                material_code=str(body["material_code"]),
                grade=grade,
                confidence=max(0.0, min(1.0, float(body["confidence"]))),
                grade_confidence=None
                if grade is None or grade_confidence is None
                else max(0.0, min(1.0, float(grade_confidence))),
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            log.warning("classification unavailable, falling back to manual selection: %s", exc)
            return None


def classifier_from_url(url: str) -> Classifier:
    return HttpClassifier(url) if url else NullClassifier()
