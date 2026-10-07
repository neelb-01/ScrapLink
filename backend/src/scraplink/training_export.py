"""Export lot photos with their confirmed material, as a training set for the ML service.

Every confirmed lot already pairs a photo with the material its seller declared. The labels are
only as good as that declaration, so by default only SETTLED lots are exported: the buyer
weighed the lot and the seller was paid, so nobody disputed what it was. `include_unsettled`
widens this to any lot past confirmation except disputed ones, for more (noisier) examples.

Output, ready for `python -m scraplink_ml.train`:

    <out>/labels.csv                    one row per photo
    <out>/<material_code>/<lot_id>.jpg  the photo, exactly as uploaded

`group` in labels.csv is the seller: photos from one seller look alike (same yard, same phone),
so the trainer keeps each seller's photos on one side of the train/test split.
"""

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Lot, LotStatus
from .storage import Storage

FIELDS = [
    "path",
    "material_code",
    "grade",
    "group",
    "lot_id",
    "status",
    "suggested_material_code",
    "suggestion_confidence",
    "photo_sha256",
]

# Past confirmation and not disputed: the seller's label stood.
_UNSETTLED = (
    LotStatus.DRAFT,
    LotStatus.LISTED,
    LotStatus.AWARDED,
    LotStatus.UNSOLD,
    LotStatus.FUNDED,
    LotStatus.PICKUP_SCHEDULED,
    LotStatus.DELIVERED,
)


@dataclass
class ExportResult:
    exported: int
    skipped: list[str]
    per_material: dict[str, int]


def export_training_set(
    db: Session, storage: Storage, out: Path, *, include_unsettled: bool = False
) -> ExportResult:
    statuses = [LotStatus.SETTLED, *(_UNSETTLED if include_unsettled else ())]
    lots = db.scalars(
        select(Lot)
        .where(Lot.status.in_(statuses), Lot.material_id.is_not(None))
        .order_by(Lot.created_at)
    )

    out.mkdir(parents=True, exist_ok=True)
    rows, skipped, per_material = [], [], {}
    for lot in lots:
        try:
            photo = storage.get(lot.photo_key)
        except OSError:
            skipped.append(f"{lot.id}: photo missing from storage")
            continue
        if hashlib.sha256(photo).hexdigest() != lot.photo_sha256:
            skipped.append(f"{lot.id}: photo does not match its recorded fingerprint")
            continue

        code = lot.material.code
        relative = PurePosixPath(code) / f"{lot.id}{PurePosixPath(lot.photo_key).suffix}"
        target = out / relative
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(photo)
        per_material[code] = per_material.get(code, 0) + 1
        rows.append(
            {
                "path": str(relative),
                "material_code": code,
                "grade": lot.grade,
                "group": str(lot.seller_id),
                "lot_id": str(lot.id),
                "status": lot.status,
                "suggested_material_code": lot.suggested_material_code or "",
                "suggestion_confidence": ""
                if lot.suggestion_confidence is None
                else f"{lot.suggestion_confidence:.4f}",
                "photo_sha256": lot.photo_sha256,
            }
        )

    with (out / "labels.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return ExportResult(len(rows), skipped, dict(sorted(per_material.items())))
