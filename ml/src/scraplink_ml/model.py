"""Zero-shot CLIP classifier.

This is a baseline, not a trained scrap classifier: CLIP has never been fine-tuned on scrap
photos, and its confidence is uncalibrated for this domain. That is acceptable only because
the backend treats every output as a suggestion: it prefills only above a confidence threshold,
the seller always confirms, and the weighbridge settles the trade. Replace with a fine-tuned
model once labelled pilot photos exist — the HTTP contract does not change.
"""

import io
from typing import Protocol

from PIL import Image, UnidentifiedImageError

from .labels import METALS, OTHER, PROMPTS

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
        """Probability per class in PROMPTS, summing to 1."""
        ...


class ClipScorer:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self.name = model_name
        self._torch = torch
        self.model = CLIPModel.from_pretrained(model_name).eval()
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.classes = list(PROMPTS)

        with torch.no_grad():
            embeddings = []
            for code in self.classes:
                tokens = self.processor(text=PROMPTS[code], return_tensors="pt", padding=True)
                text = self._features(self.model.get_text_features(**tokens))
                mean = text.mean(dim=0)
                embeddings.append(mean / mean.norm())
            self.text = torch.stack(embeddings)

    @staticmethod
    def _features(output):
        # transformers 5 can return a model-output object instead of a bare tensor.
        tensor = getattr(output, "pooler_output", output)
        return tensor / tensor.norm(dim=-1, keepdim=True)

    def scores(self, image: Image.Image) -> dict[str, float]:
        torch = self._torch
        with torch.no_grad():
            pixels = self.processor(images=image, return_tensors="pt")
            features = self._features(self.model.get_image_features(**pixels))[0]
            logits = self.model.logit_scale.exp() * (self.text @ features)
            probabilities = logits.softmax(dim=0).tolist()
        return dict(zip(self.classes, probabilities, strict=True))


def suggest(scores: dict[str, float]) -> dict:
    """Shape scores into the backend contract.

    The answer is always the most likely *metal*, with that metal's own probability as its
    confidence. When the photo looks like something else entirely, that probability is low
    and the backend does not prefill.
    """
    best = max(METALS, key=lambda code: scores[code])
    return {
        "material_code": best,
        "grade": None,  # zero-shot grade from a photo is not credible; the seller chooses
        "confidence": round(scores[best], 4),
        "looks_like_scrap_metal": scores[OTHER] < max(scores[m] for m in METALS),
        "scores": {code: round(p, 4) for code, p in sorted(scores.items(), key=lambda kv: -kv[1])},
    }
