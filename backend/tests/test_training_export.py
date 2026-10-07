import csv
import hashlib
import uuid
from datetime import timedelta

from helpers import SLIP, create_lot, funded_lot, settled_lot
from sqlalchemy import select

from scraplink.models import Lot
from scraplink.training_export import export_training_set


def _rows(out):
    with (out / "labels.csv").open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def test_exports_settled_lots_with_their_photo_and_seller_group(
    app, client, db, clock, tmp_path, seller, buyer
):
    settled = settled_lot(client, clock, seller, buyer, weighed=100_000, material="brass")
    funded_lot(client, clock, seller, buyer)  # sold, not yet settled
    create_lot(client, seller)  # never confirmed: no label at all

    out = tmp_path / "set"
    result = export_training_set(db, app.state.env.storage, out)

    assert result.exported == 1
    assert result.per_material == {"brass": 1}
    [row] = _rows(out)
    assert row["lot_id"] == settled["id"]
    assert row["material_code"] == "brass"
    assert row["group"] == seller.id
    photo = (out / row["path"]).read_bytes()
    assert hashlib.sha256(photo).hexdigest() == row["photo_sha256"] == settled["photo_sha256"]


def test_unsettled_lots_are_opt_in_and_disputed_ones_never(
    app, client, db, clock, tmp_path, seller, buyer
):
    funded_lot(client, clock, seller, buyer)
    # Disputed: weighed at five times what escrow covers, so settlement is blocked.
    lot_id = funded_lot(client, clock, seller, buyer, grams=10_000)
    client.post(
        f"/lots/{lot_id}/pickup",
        headers=seller.headers,
        json={"pickup_at": (clock.now + timedelta(days=1)).isoformat()},
    )
    client.post(
        f"/lots/{lot_id}/delivery",
        headers=buyer.headers,
        data={"measured_weight_grams": "50000"},
        files={"slip": SLIP},
    )
    lot = client.post(f"/lots/{lot_id}/delivery/accept", headers=seller.headers).json()
    assert lot["status"] == "disputed"

    assert export_training_set(db, app.state.env.storage, tmp_path / "a").exported == 0
    wider = export_training_set(db, app.state.env.storage, tmp_path / "b", include_unsettled=True)
    assert wider.exported == 1
    assert [r["status"] for r in _rows(tmp_path / "b")] == ["funded"]


def test_a_photo_that_no_longer_matches_its_fingerprint_is_skipped(
    app, client, db, clock, tmp_path, seller, buyer
):
    settled = settled_lot(client, clock, seller, buyer, weighed=100_000)
    lot = db.scalars(select(Lot).where(Lot.id == uuid.UUID(settled["id"]))).one()
    path = app.state.env.storage._path(lot.photo_key)
    path.write_bytes(b"replaced")

    result = export_training_set(db, app.state.env.storage, tmp_path / "set")
    assert result.exported == 0
    assert "fingerprint" in result.skipped[0]
