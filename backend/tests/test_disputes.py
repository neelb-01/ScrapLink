"""A disputed trade is no longer a dead end: an admin settles it at an agreed weight or cancels."""

import uuid
from datetime import timedelta

from helpers import SLIP, funded_lot
from sqlalchemy import func, select

from scraplink import custody
from scraplink.models import LedgerPosting


def _weighed(client, clock, seller, buyer, *, declared_kg: int, weighed_kg: float) -> str:
    """Copper at the reference rate (₹680/kg), collected and weighed."""
    lot_id = funded_lot(client, clock, seller, buyer, grams=declared_kg * 1000)
    pickup_at = (clock.now + timedelta(days=1)).isoformat()
    client.post(f"/lots/{lot_id}/pickup", headers=seller.headers, json={"pickup_at": pickup_at})
    response = client.post(
        f"/lots/{lot_id}/delivery",
        headers=buyer.headers,
        data={"measured_weight_grams": str(round(weighed_kg * 1000))},
        files={"slip": SLIP},
    )
    assert response.status_code == 200, response.text
    return lot_id


def _resolve(client, party, lot_id, **body):
    return client.post(f"/lots/{lot_id}/dispute/resolve", headers=party.headers, json=body)


def _balance(client, party):
    return client.get("/wallet", headers=party.headers).json()["balance_paise"]


def test_admin_settles_a_disputed_reading_at_the_agreed_weight(
    client, db, clock, admin, seller, buyer
):
    lot_id = _weighed(client, clock, seller, buyer, declared_kg=100, weighed_kg=80)
    reason = {"reason": "We loaded 100 kg; the slip says 80."}
    lot = client.post(f"/lots/{lot_id}/delivery/dispute", headers=seller.headers, json=reason)
    assert lot.json()["dispute"] == {
        "raised_by": "seller",
        "reason": "We loaded 100 kg; the slip says 80.",
        "raised_at": lot.json()["dispute"]["raised_at"],
    }

    response = _resolve(
        client, admin, lot_id, outcome="settle", weight_grams=98_000, note="Re-weighed at 98 kg"
    )
    assert response.status_code == 200, response.text
    lot = response.json()
    assert lot["status"] == "settled"
    assert lot["dispute"] is None
    assert lot["measured_weight_grams"] == 80_000  # the weighbridge reading is kept as it was
    assert lot["settled_weight_grams"] == 98_000
    assert lot["settled_amount_paise"] == 6_664_000  # 68_000 x 98 kg
    assert lot["certificate_id"] is not None

    assert _balance(client, seller) == 6_664_000
    assert _balance(client, buyer) == 7_480_000 - 6_664_000  # escrow was 100 kg x 1.10
    assert db.scalar(select(func.sum(LedgerPosting.amount_paise))) == 0

    events = custody.lot_events(db, uuid.UUID(lot_id))
    assert custody.verify_chain(events).valid
    resolved = next(e for e in events if e.event_type == "dispute.resolved")
    assert resolved.payload["note"] == "Re-weighed at 98 kg"
    assert resolved.actor_id is not None

    invoice = client.get(f"/lots/{lot_id}/invoice", headers=buyer.headers).json()
    assert invoice["quantity_grams"] == 98_000


def test_settling_cannot_pay_out_more_than_escrow_holds(client, clock, admin, seller, buyer):
    lot_id = _weighed(client, clock, seller, buyer, declared_kg=100, weighed_kg=150)
    lot = client.post(f"/lots/{lot_id}/delivery/accept", headers=seller.headers).json()
    assert lot["status"] == "disputed"
    assert lot["dispute"]["raised_by"] == "escrow"

    [listed] = client.get("/admin/disputes", headers=admin.headers).json()
    assert listed["escrow_held_paise"] == 7_480_000
    assert listed["max_settle_weight_grams"] == 110_000

    too_much = _resolve(
        client, admin, lot_id, outcome="settle", weight_grams=150_000, note="As weighed"
    )
    assert too_much.status_code == 409
    assert "110 kg or less" in too_much.json()["detail"]

    ok = _resolve(client, admin, lot_id, outcome="settle", weight_grams=110_000, note="Capped")
    assert ok.json()["status"] == "settled"
    assert _balance(client, seller) == 7_480_000
    assert _balance(client, buyer) == 0
    assert client.get("/admin/disputes", headers=admin.headers).json() == []


def test_cancelling_returns_the_whole_escrow_to_the_buyer(client, db, clock, admin, seller, buyer):
    lot_id = _weighed(client, clock, seller, buyer, declared_kg=100, weighed_kg=60)
    client.post(
        f"/lots/{lot_id}/delivery/dispute", headers=seller.headers, json={"reason": "Wrong lot"}
    )
    lot = _resolve(client, admin, lot_id, outcome="cancel", note="Wrong lot collected").json()
    assert lot["status"] == "cancelled"
    assert lot["certificate_id"] is None
    assert _balance(client, buyer) == 7_480_000
    assert _balance(client, seller) == 0
    assert db.scalar(select(func.sum(LedgerPosting.amount_paise))) == 0


def test_only_an_admin_resolves_and_only_a_disputed_lot(client, clock, admin, seller, buyer):
    lot_id = _weighed(client, clock, seller, buyer, declared_kg=100, weighed_kg=80)
    assert _resolve(client, admin, lot_id, outcome="cancel", note="Early").status_code == 409
    client.post(f"/lots/{lot_id}/delivery/dispute", headers=seller.headers, json={"reason": "Low"})
    assert _resolve(client, seller, lot_id, outcome="cancel", note="Mine").status_code == 403
    assert _resolve(client, admin, lot_id, outcome="settle", note="No weight").status_code == 422
    assert _resolve(client, admin, lot_id, outcome="cancel", note="ok").status_code == 422  # short
