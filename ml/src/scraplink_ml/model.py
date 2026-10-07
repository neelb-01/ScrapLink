"""Material suggestion from a photo.

Two scorers share one CLIP image encoder:

- ZeroShotScorer, the baseline: CLIP compares the photo with text descriptions of each metal
  (labels.py). It has never seen scrap, and its confidence is uncalibrated for this domain.
- ProbeScorer: a small classifier trained on CLIP's features of real, labelled lot photos
  (train.py). Used when SCRAPLINK_ML_PROBE points at a trained probe file.

Either way the backend treats the output as a suggestion: it prefills only above a confidence
threshold, the seller always confirms, and the weighbridge settles the trade. The HTTP contract
is the same for both.
"""

import io
from typing import Protocol

from PIL import Image, UnidentifiedImageError

from .labels import OTHER, PROMPTS
from .probe import Probe

DEFAULT_MODEL = "openai/clip-vit-base-patch32"


class NotAnImage(ValueError):
    pass


def load_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise NotAnImage("the upload is not a readable image") from exc
    return image.convert("RGB")


class Scorer(Protocol):
    name: str

    def scores(self, image: Image.Image) -> dict[str, float]:
        """Probability per class, summing to 1."""
        ...


class Embedder(Protocol):
    name: str

    def image(self, image: Image.Image) -> list[float]:
        """Unit-length feature vector for one photo."""
        ...


class ClipEmbedder:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self.name = model_name
        self._torch = torch
        self.model = CLIPModel.from_pretrained(model_name).eval()
        self.processor = CLIPProcessor.from_pretrained(model_name)

    @staticmethod
    def _unit(output):
        # transformers 5 can return a model-output object instead of a bare tensor.
        tensor = getattr(output, "pooler_output", output)
        return tensor / tensor.norm(dim=-1, keepdim=True)

    def image(self, image: Image.Image) -> list[float]:
        with self._torch.no_grad():
            pixels = self.processor(images=image, return_tensors="pt")
            return self._unit(self.model.get_image_features(**pixels))[0].tolist()

    def text(self, prompts: list[str]) -> list[float]:
        """One unit vector for several phrasings of a class (prompt ensembling)."""
        with self._torch.no_grad():
            tokens = self.processor(text=prompts, return_tensors="pt", padding=True)
            mean = self._unit(self.model.get_text_features(**tokens)).mean(dim=0)
            return (mean / mean.norm()).tolist()

    def logit_scale(self) -> float:
        return float(self.model.logit_scale.detach().exp())


class ZeroShotScorer:
    def __init__(self, embedder: ClipEmbedder):
        import torch

        self._torch = torch
        self.embedder = embedder
        self.name = embedder.name
        self.classes = list(PROMPTS)
        self.text = torch.tensor([embedder.text(PROMPTS[code]) for code in self.classes])
        self.scale = embedder.logit_scale()

    def scores_for(self, features: list[float]) -> dict[str, float]:
        logits = self.scale * (self.text @ self._torch.tensor(features))
        return dict(zip(self.classes, logits.softmax(dim=0).tolist(), strict=True))

    def scores(self, image: Image.Image) -> dict[str, float]:
        return self.scores_for(self.embedder.image(image))


class ClipScorer(ZeroShotScorer):
    """The zero-shot baseline with its own CLIP model: the service's default."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        super().__init__(ClipEmbedder(model_name))


class ProbeScorer:
    def __init__(self, probe: Probe, embedder: Embedder):
        if probe.embedding_model != embedder.name:
            raise ValueError(
                f"probe was trained on {probe.embedding_model} features, not {embedder.name}"
            )
        self.probe = probe
        self.embedder = embedder
        self.name = f"{embedder.name}+probe({probe.trained_at})"

    def scores(self, image: Image.Image) -> dict[str, float]:
        return self.probe.probabilities(self.embedder.image(image))


def suggest(scores: dict[str, float]) -> dict:
    """Shape scores into the backend contract.

    The answer is always the most likely *material*, with its own probability as the
    confidence. When the photo looks like something else entirely (OTHER, if the scorer has
    that class), that probability is low and the backend does not prefill.
    """
    candidates = [code for code in scores if code != OTHER]
    best = max(candidates, key=lambda code: scores[code])
    return {
        "material_code": best,
        "grade": None,  # grade from a photo is not credible yet; the seller chooses
        "confidence": round(scores[best], 4),
        "looks_like_scrap_metal": scores.get(OTHER, 0.0) < scores[best],
        "scores": {code: round(p, 4) for code, p in sorted(scores.items(), key=lambda kv: -kv[1])},
    }
