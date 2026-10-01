"""The first slice's definition of done: one trade, photo to verifiable certificate."""

import hashlib
from datetime import timedelta

from helpers import SLIP, bid, create_lot
from sqlalchemy import func, select

from scraplink.classification import Suggestion
from scraplink.models import CustodyEvent, LedgerAccount, LedgerPosting


def test_photo_to_certificate(client, db, clock, classifier, register, seller):
    buyer_a = register("buyer")
    buyer_b = register("buyer")
    classifier.next = Suggestion("copper", "A", 0.91)

    # 1. Photo: the model's confident suggestion is offered for prefill.
    lot = create_lot(client, seller)
    lot_id = lot["id"]
    assert lot["status"] == "draft"
    assert lot["classification"] == {
        "suggested_material_code": "copper",
        "suggested_grade": "A",
        "confidence": 0.91,
        "prefilled": True,
        "threshold": 0.75,
    }

    # 2. Confirm: the seller overrides the grade — the human has the final word.
    response = client.post(
        f"/lots/{lot_id}/confirm",
        headers=seller.headers,
        json={"material_code": "copper", "grade": "B", "declared_weight_grams": 250_000},
    )
    assert response.status_code == 200, response.text
    assert response.json()["estimate"] == {
        "reference_rate_paise_per_kg": 68_000,
        "rate_paise_per_kg": 57_800,  # grade B = 0.85 x reference
        "total_paise": 14_450_000,  # 250 kg
        "low_paise": 13_005_000,
        "high_paise": 15_895_000,
    }

    # 3. List for sealed bids.
    response = client.post(
        f"/lots/{lot_id}/list",
        headers=seller.headers,
        json={"auction_hours": 24, "reserve_rate_paise_per_kg": 55_000},
    )
    assert response.json()["status"] == "listed"

    market = client.get("/lots", params={"scope": "market"}, headers=buyer_a.headers).json()
    assert [m["id"] for m in market] == [lot_id]
    assert market[0]["reserve_rate_paise_per_kg"] is None  # reserve stays private

    assert bid(client, buyer_a, lot_id, 58_000).status_code == 200
    assert bid(client, buyer_b, lot_id, 59_500).status_code == 200
    revised = bid(client, buyer_a, lot_id, 59_000).json()
    assert revised["my_bid_rate_paise_per_kg"] == 59_000
    assert revised["bid_count"] == 2

    # Sealed: nobody sees competing bids while the auction is open.
    own = client.get(f"/lots/{lot_id}/bids", headers=buyer_a.headers).json()
    assert [b["rate_paise_per_kg"] for b in own] == [59_000]
    assert client.get(f"/lots/{lot_id}/bids", headers=seller.headers).json() == []

    # 4. Close: highest rate wins.
    clock.advance(hours=25)
    lot = client.get(f"/lots/{lot_id}", headers=seller.headers).json()
    assert lot["status"] == "awarded"
    assert lot["award"]["buyer"]["id"] == buyer_b.id
    assert lot["award"]["rate_paise_per_kg"] == 59_500
    ranked = client.get(f"/lots/{lot_id}/bids", headers=seller.headers).json()
    assert [b["rate_paise_per_kg"] for b in ranked] == [59_500, 59_000]

    # 5. Escrow: only the winner can fund; funding covers declared weight + 10% tolerance.
    assert client.post(f"/lots/{lot_id}/escrow", headers=buyer_a.headers).status_code == 403
    escrow = client.post(f"/lots/{lot_id}/escrow", headers=buyer_b.headers).json()
    assert escrow["gateway"] == "simulated"
    assert escrow["amount_paise"] == 16_362_500  # 59_500 x 250 kg x 1.10
    response = client.post(
        f"/payments/{escrow['intent_id']}/simulate-capture", headers=buyer_b.headers
    )
    assert response.json()["status"] == "captured"
    assert client.get(f"/lots/{lot_id}", headers=seller.headers).json()["status"] == "funded"

    # 6. Pickup, then the weighbridge says 243.5 kg, not 250.
    pickup_at = (clock.now + timedelta(days=1)).isoformat()
    response = client.post(
        f"/lots/{lot_id}/pickup", headers=seller.headers, json={"pickup_at": pickup_at}
    )
    assert response.json()["status"] == "pickup_scheduled"
    response = client.post(
        f"/lots/{lot_id}/delivery",
        headers=buyer_b.headers,
        data={"measured_weight_grams": "243500"},
        files={"slip": SLIP},
    )
    assert response.json()["status"] == "delivered"

    # 7. Seller accepts: settlement recomputes from the measured weight.
    lot = client.post(f"/lots/{lot_id}/delivery/accept", headers=seller.headers).json()
    assert lot["status"] == "settled"
    assert lot["settled_amount_paise"] == 14_488_250  # 59_500 x 243.5 kg
    assert client.get("/wallet", headers=seller.headers).json()["balance_paise"] == 14_488_250
    assert client.get("/wallet", headers=buyer_b.headers).json()["balance_paise"] == 1_874_250
    assert client.get("/wallet", headers=buyer_a.headers).json()["balance_paise"] == 0

    escrow_account = db.scalars(
        select(LedgerAccount).where(LedgerAccount.key == f"escrow:{lot_id}")
    ).one()
    escrow_left = db.scalar(
        select(func.sum(LedgerPosting.amount_paise)).where(
            LedgerPosting.account_id == escrow_account.id
        )
    )
    assert escrow_left == 0
    assert db.scalar(select(func.sum(LedgerPosting.amount_paise))) == 0

    # 8. Certificate: the PDF is what was fingerprinted, and the chain verifies.
    events = client.get(f"/lots/{lot_id}/custody", headers=buyer_b.headers).json()
    assert [e["event_type"] for e in events] == [
        "lot.created",
        "lot.confirmed",
        "lot.listed",
        "auction.closed",
        "escrow.funded",
        "pickup.scheduled",
        "delivery.recorded",
        "delivery.accepted",
        "settlement.completed",
    ]
    assert events[1]["payload"]["suggestion_accepted"] is False

    cert = client.get(f"/certificates/{lot['certificate_id']}", headers=buyer_b.headers).json()
    assert cert["head_hash"] == events[-1]["hash"]
    assert cert["verify_url"] == f"https://scraplink.test/certificates/{cert['id']}/verify"
    pdf = client.get(cert["pdf_url"], headers=seller.headers)
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert hashlib.sha256(pdf.content).hexdigest() == cert["pdf_sha256"]

    verification = client.get(f"/certificates/{cert['id']}/verify").json()  # no auth: public
    assert verification["valid"] is True

    # 9. Tamper with history: inflate the recorded weighbridge weight.
    recorded = db.scalars(
        select(CustodyEvent).where(
            CustodyEvent.lot_id == escrow_account.lot_id, CustodyEvent.seq == 7
        )
    ).one()
    recorded.payload = {**recorded.payload, "measured_weight_grams": 250_000}
    db.commit()

    verification = client.get(f"/certificates/{cert['id']}/verify").json()
    assert verification["valid"] is False
    assert verification["reason"] == "event 7 was altered after it was recorded"
