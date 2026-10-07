"""A trained linear probe: softmax(W · features + b) over material codes.

Small enough to keep as JSON (classes x 512 numbers for CLIP ViT-B/32), and it needs only numpy
to run, so loading it adds nothing to the service's start-up beyond the CLIP model itself.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Probe:
    classes: list[str]
    weight: list[list[float]]  # one row per class
    bias: list[float]
    embedding_model: str
    trained_at: str
    # How it did on photos held out from training, and how many photos it learned from.
    evaluation: dict = field(default_factory=dict)

    def probabilities(self, features: list[float]) -> dict[str, float]:
        logits = np.asarray(self.weight) @ np.asarray(features) + np.asarray(self.bias)
        exp = np.exp(logits - logits.max())
        return dict(zip(self.classes, (exp / exp.sum()).tolist(), strict=True))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self)), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Probe":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))
