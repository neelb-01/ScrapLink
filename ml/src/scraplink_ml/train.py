"""Train a material classifier on labelled lot photos.

    python -m scraplink_ml.train --data ../training-data --out models/probe.json

`--data` is a folder written by the backend's `python -m scraplink.cli export-training`:
labels.csv plus the photos. Add `--negatives <folder of non-scrap photos>` (people, rooms,
cardboard, blurry shots) to teach it an "other" class, so photos that aren't scrap come back
with low confidence instead of a confident wrong material.

How it works: CLIP stays frozen and turns each photo into a 512-number feature vector, once.
A linear classifier (multinomial logistic regression) is trained on those vectors. This is the
right first step with hundreds, not tens of thousands, of photos: it trains in seconds on a CPU
and can't drift far from what CLIP already knows.

Honest evaluation: each seller's photos go entirely to training or entirely to testing, because
one seller's photos share a yard, a phone and a light, and splitting them would flatter the
score. The report gives per-material precision and recall, a confusion table, the zero-shot
baseline on the same held-out photos, and the prefill threshold that keeps wrong prefills rare.
The saved probe is then refitted on every photo.
"""

import argparse
import csv
import random
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .labels import METALS, OTHER
from .model import ClipEmbedder, Embedder, ZeroShotScorer, load_image
from .probe import Probe

THRESHOLDS = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class Example:
    path: Path
    label: str
    group: str


# --- data ------------------------------------------------------------------------------------


def read_dataset(data: Path, negatives: Path | None = None) -> list[Example]:
    with (data / "labels.csv").open(encoding="utf-8") as file:
        examples = [
            Example(data / row["path"], row["material_code"], row["group"])
            for row in csv.DictReader(file)
        ]
    if negatives is not None:
        examples += [
            # Each negative photo is its own group: they come from anywhere.
            Example(path, OTHER, f"negative:{path.name}")
            for path in sorted(negatives.iterdir())
            if path.suffix.lower() in IMAGE_SUFFIXES
        ]
    return examples


def drop_rare(examples: list[Example], min_per_class: int) -> tuple[list[Example], dict[str, int]]:
    counts = Counter(e.label for e in examples)
    rare = {label: n for label, n in counts.items() if n < min_per_class}
    return [e for e in examples if e.label not in rare], rare


def group_split(
    examples: list[Example], test_fraction: float, seed: int
) -> tuple[list[int], list[int], bool]:
    """Indices for training and testing. True when whole groups were kept together; False when
    there were too few groups and photos had to be split individually (an optimistic test)."""
    rng = random.Random(seed)
    groups = sorted({e.group for e in examples})
    if len(groups) < 2:
        order = list(range(len(examples)))
        rng.shuffle(order)
        cut = max(1, round(len(order) * test_fraction))
        return sorted(order[cut:]), sorted(order[:cut]), False

    rng.shuffle(groups)
    wanted = len(examples) * test_fraction
    test_groups: set[str] = set()
    size = 0
    for group in groups[:-1]:  # always leave at least one group to train on
        if size >= wanted:
            break
        test_groups.add(group)
        size += sum(1 for e in examples if e.group == group)
    test = [i for i, e in enumerate(examples) if e.group in test_groups]
    train = [i for i, e in enumerate(examples) if e.group not in test_groups]
    return train, test, True


# --- model -----------------------------------------------------------------------------------


def fit(
    features: np.ndarray, labels: list[str], classes: list[str], l2: float = 1e-3
) -> tuple[np.ndarray, np.ndarray]:
    """Class-balanced multinomial logistic regression, full batch, L-BFGS."""
    import torch

    x = torch.tensor(features, dtype=torch.float32)
    y = torch.tensor([classes.index(label) for label in labels])
    counts = torch.bincount(y, minlength=len(classes)).clamp(min=1).float()
    balance = len(labels) / (len(classes) * counts)  # rare materials count as much as common

    weight = torch.zeros(len(classes), x.shape[1], requires_grad=True)
    bias = torch.zeros(len(classes), requires_grad=True)
    optimiser = torch.optim.LBFGS([weight, bias], max_iter=500, line_search_fn="strong_wolfe")
    loss_fn = torch.nn.CrossEntropyLoss(weight=balance)

    def closure():
        optimiser.zero_grad()
        loss = loss_fn(x @ weight.T + bias, y) + l2 * weight.pow(2).sum()
        loss.backward()
        return loss

    optimiser.step(closure)
    return weight.detach().numpy(), bias.detach().numpy()


def _probabilities(weight: np.ndarray, bias: np.ndarray, features: np.ndarray) -> np.ndarray:
    logits = features @ weight.T + bias
    exp = np.exp(logits - logits.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


# --- evaluation ------------------------------------------------------------------------------


def evaluate(scores: list[dict[str, float]], labels: list[str]) -> dict:
    """Judge suggestions the way the backend uses them: the most likely material (never OTHER)
    and its probability. A negative photo is handled well only if it isn't prefilled."""
    picks = []
    for s in scores:
        best = max((c for c in s if c != OTHER), key=lambda c: s[c])
        picks.append((best, s[best]))

    materials = [i for i, label in enumerate(labels) if label != OTHER]
    correct = [i for i in materials if picks[i][0] == labels[i]]
    per_class = {}
    for label in sorted({labels[i] for i in materials}):
        support = sum(1 for i in materials if labels[i] == label)
        predicted = sum(1 for p, _ in picks if p == label)
        hits = sum(1 for i in correct if labels[i] == label)
        per_class[label] = {
            "support": support,
            "recall": round(hits / support, 3),
            "precision": round(hits / predicted, 3) if predicted else None,
        }

    confusion: dict[str, dict[str, int]] = {}
    for (pick, _), label in zip(picks, labels, strict=True):
        row = confusion.setdefault(label, {})
        row[pick] = row.get(pick, 0) + 1

    table = []
    for t in THRESHOLDS:
        prefilled = [i for i, (_, conf) in enumerate(picks) if conf >= t]
        right = [i for i in prefilled if picks[i][0] == labels[i]]
        table.append(
            {
                "threshold": t,
                "prefilled": len(prefilled),
                "coverage": round(len(prefilled) / len(labels), 3),
                "precision": round(len(right) / len(prefilled), 3) if prefilled else None,
            }
        )
    return {
        "photos": len(labels),
        "accuracy": round(len(correct) / len(materials), 3) if materials else None,
        "per_class": per_class,
        "confusion": confusion,
        "thresholds": table,
    }


def suggest_threshold(table: list[dict], target_precision: float) -> float | None:
    """The lowest threshold whose prefills were right at least `target_precision` of the time."""
    for row in table:
        if row["prefilled"] and row["precision"] >= target_precision:
            return row["threshold"]
    return None


# --- the run ---------------------------------------------------------------------------------


def run(
    data: Path,
    out: Path,
    embedder: Embedder,
    *,
    negatives: Path | None = None,
    min_per_class: int = 5,
    test_fraction: float = 0.25,
    target_precision: float = 0.95,
    seed: int = 0,
    log=print,
) -> dict:
    examples, rare = drop_rare(read_dataset(data, negatives), min_per_class)
    for label, n in sorted(rare.items()):
        log(f"left out {label}: {n} photos, fewer than --min-per-class {min_per_class}")
    classes = sorted({e.label for e in examples})
    if len(classes) < 2:
        raise SystemExit("need at least two materials with enough photos to train a classifier")

    log(f"reading {len(examples)} photos with {embedder.name}")
    features = np.array([embedder.image(load_image(e.path.read_bytes())) for e in examples])
    labels = [e.label for e in examples]

    train, test, grouped = group_split(examples, test_fraction, seed)
    weight, bias = fit(features[train], [labels[i] for i in train], classes)
    held_out = [labels[i] for i in test]
    probe_scores = [
        dict(zip(classes, row.tolist(), strict=True))
        for row in _probabilities(weight, bias, features[test])
    ]
    report = {
        "trained_on": dict(sorted(Counter(labels).items())),
        "split_by_seller": grouped,
        "held_out": evaluate(probe_scores, held_out),
    }
    report["suggested_threshold"] = suggest_threshold(
        report["held_out"]["thresholds"], target_precision
    )
    report["target_precision"] = target_precision

    if hasattr(embedder, "text"):  # a CLIP embedder can also run the zero-shot baseline
        zero = ZeroShotScorer(embedder)
        zero_scores = [zero.scores_for(features[i].tolist()) for i in test]
        report["zero_shot_baseline"] = evaluate(zero_scores, held_out)

    # The held-out score is in hand; the probe that ships learns from every photo.
    weight, bias = fit(features, labels, classes)
    probe = Probe(
        classes=classes,
        weight=weight.tolist(),
        bias=bias.tolist(),
        embedding_model=embedder.name,
        trained_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        evaluation=report,
    )
    probe.save(out)
    out.with_suffix(".report.txt").write_text(format_report(report), encoding="utf-8")
    log(format_report(report))
    log(f"saved {out} (report beside it)")
    return report


def _pct(value: float | None) -> str:
    return "  -  " if value is None else f"{value * 100:4.0f}%"


def format_report(report: dict) -> str:
    held = report["held_out"]
    lines = ["", f"Trained on: {report['trained_on']}"]
    if not report["split_by_seller"]:
        lines.append(
            "WARNING: every photo is from one seller, so test photos resemble training photos "
            "and the scores below are optimistic."
        )
    if held["photos"] < 30:
        lines.append(f"WARNING: only {held['photos']} held-out photos; read these numbers loosely.")

    lines += ["", f"Held-out photos: {held['photos']}   accuracy {_pct(held['accuracy'])}"]
    baseline = report.get("zero_shot_baseline")
    if baseline:
        lines.append(f"Zero-shot baseline, same photos: accuracy {_pct(baseline['accuracy'])}")
        if any(label not in METALS for label in held["per_class"]):
            lines.append("  (the baseline knows only metals, so it misses every non-metal photo)")

    lines += ["", f"{'material':<22}{'photos':>7}{'precision':>11}{'recall':>8}"]
    for label, row in held["per_class"].items():
        lines.append(
            f"{label:<22}{row['support']:>7}{_pct(row['precision']):>11}{_pct(row['recall']):>8}"
        )

    lines += ["", "Mistakes (actual -> suggested: photos):"]
    mistakes = [
        f"  {actual} -> {pick}: {n}"
        for actual, row in held["confusion"].items()
        for pick, n in row.items()
        if pick != actual
    ]
    lines += mistakes or ["  none"]

    lines += ["", f"{'threshold':>9}{'prefilled':>11}{'right':>8}"]
    for row in held["thresholds"]:
        lines.append(f"{row['threshold']:>9}{_pct(row['coverage']):>11}{_pct(row['precision']):>8}")
    suggested = report["suggested_threshold"]
    target = report["target_precision"]
    lines.append(
        f"\nSet ML_CLASSIFICATION_CONFIDENCE_THRESHOLD={suggested} for prefills right at least "
        f"{target:.0%} of the time."
        if suggested is not None
        else f"\nNo threshold kept prefills right {target:.0%} of the time: keep the current one."
    )
    if not any(label in METALS for label in report["trained_on"]):
        lines.append("Note: no metal photos were in the training set.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m scraplink_ml.train", description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="folder from export-training")
    parser.add_argument("--out", type=Path, default=Path("models/probe.json"))
    parser.add_argument("--negatives", type=Path, help="folder of photos that aren't scrap")
    parser.add_argument("--min-per-class", type=int, default=5)
    parser.add_argument("--test-fraction", type=float, default=0.25)
    parser.add_argument("--target-precision", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model", default="openai/clip-vit-base-patch32")
    args = parser.parse_args(argv)
    if not (args.data / "labels.csv").exists():
        sys.exit(f"{args.data} has no labels.csv: run the backend's export-training first")
    run(
        args.data,
        args.out,
        ClipEmbedder(args.model),
        negatives=args.negatives,
        min_per_class=args.min_per_class,
        test_fraction=args.test_fraction,
        target_precision=args.target_precision,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
