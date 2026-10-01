import hashlib
import hmac
import json
from datetime import datetime, timedelta

import pytest
from helpers import SLIP, bid, create_lot, listed_lot

from scraplink.payments import RazorpayGateway


def _award(client, clock, seller, buyer, *, grams=100_000, rate=70_000) -> str:
    lot_id = listed_lot(client, seller, grams=grams)
    assert bid(client, buyer, lot_id, rate).status_code == 200
    clock.advance(hours=25)
    assert client.get(f"/lots/{lot_id}", headers=seller.headers).json()["status"] == "awarded"
    return lot_id


def _fund_and_deliver(client, clock, seller, buyer, lot_id, measured_grams: int) -> None:
    escrow = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()
    client.post(f"/payments/{escrow['intent_id']}/simulate-capture", headers=buyer.headers)
    client.post(
        f"/lots/{lot_id}/pickup",
        headers=buyer.headers,
        json={"pickup_at": (clock.now + timedelta(hours=4)).isoformat()},
    )
    response = client.post(
        f"/lots/{lot_id}/delivery",
        headers=buyer.headers,
        data={"measured_weight_grams": str(measured_grams)},
        files={"slip": SLIP},
    )
    assert response.status_code == 200, response.text


# --- auction ---------------------------------------------------------------------------------


def test_only_approved_buyers_bid(client, register, seller):
    lot_id = listed_lot(client, seller)
    assert bid(client, seller, lot_id, 60_000).status_code == 403
    pending = register("buyer", approve=False)
    assert bid(client, pending, lot_id, 60_000).status_code == 403


def test_cannot_list_before_confirming(client, seller):
    lot_id = create_lot(client, seller)["id"]
    response = client.post(f"/lots/{lot_id}/list", headers=seller.headers, json={})
    assert response.status_code == 409


def test_bidding_closes_at_deadline(client, clock, seller, buyer):
    lot_id = listed_lot(client, seller, hours=2)
    clock.advance(hours=2)
    response = bid(client, buyer, lot_id, 60_000)
    assert response.status_code == 409
    # The deadline passing is recorded even though the bid failed.
    assert client.get(f"/lots/{lot_id}", headers=seller.headers).json()["status"] == "unsold"


def test_reserve_not_met_leaves_lot_unsold(client, clock, seller, buyer):
    lot_id = listed_lot(client, seller, reserve=65_000)
    bid(client, buyer, lot_id, 64_999)
    clock.advance(days=2)
    lot = client.get(f"/lots/{lot_id}", headers=seller.headers).json()
    assert lot["status"] == "unsold"
    assert lot["award"] is None


def test_equal_bids_go_to_the_earlier_one(client, clock, register, seller):
    first, second = register("buyer"), register("buyer")
    lot_id = listed_lot(client, seller)
    bid(client, first, lot_id, 60_000)
    clock.advance(minutes=5)
    bid(client, second, lot_id, 60_000)
    clock.advance(days=2)
    lot = client.get(f"/lots/{lot_id}", headers=seller.headers).json()
    assert lot["award"]["buyer"]["id"] == first.id


def test_market_hides_unlisted_and_other_parties_lots(client, clock, register, seller, buyer):
    outsider = register("buyer")
    draft_id = create_lot(client, seller)["id"]
    lot_id = _award(client, clock, seller, buyer)

    assert client.get("/lots", params={"scope": "market"}, headers=outsider.headers).json() == []
    assert client.get(f"/lots/{draft_id}", headers=outsider.headers).status_code == 404
    assert client.get(f"/lots/{lot_id}", headers=outsider.headers).status_code == 404
    # The winner sees the award; buyers on an open lot do not see the custody record.
    assert client.get(f"/lots/{lot_id}", headers=buyer.headers).json()["award"] is not None
    open_id = listed_lot(client, seller)
    assert client.get(f"/lots/{open_id}", headers=outsider.headers).status_code == 200
    assert client.get(f"/lots/{open_id}/custody", headers=outsider.headers).status_code == 404


# --- escrow and settlement -------------------------------------------------------------------


def test_escrow_intent_is_reused_until_paid(client, clock, seller, buyer):
    lot_id = _award(client, clock, seller, buyer)
    first = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()
    again = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()
    assert first["intent_id"] == again["intent_id"]


def test_weight_within_tolerance_settles(client, clock, seller, buyer):
    lot_id = _award(client, clock, seller, buyer, grams=100_000, rate=70_000)
    _fund_and_deliver(client, clock, seller, buyer, lot_id, measured_grams=110_000)  # +10%
    lot = client.post(f"/lots/{lot_id}/delivery/accept", headers=seller.headers).json()
    assert lot["status"] == "settled"
    assert lot["settled_amount_paise"] == 7_700_000
    assert client.get("/wallet", headers=buyer.headers).json()["balance_paise"] == 0


def test_weight_over_tolerance_blocks_settlement(client, clock, seller, buyer):
    lot_id = _award(client, clock, seller, buyer, grams=100_000, rate=70_000)
    _fund_and_deliver(client, clock, seller, buyer, lot_id, measured_grams=112_000)
    lot = client.post(f"/lots/{lot_id}/delivery/accept", headers=seller.headers).json()
    assert lot["status"] == "disputed"
    assert lot["certificate_id"] is None
    assert client.get("/wallet", headers=seller.headers).json()["balance_paise"] == 0
    events = client.get(f"/lots/{lot_id}/custody", headers=seller.headers).json()
    assert events[-1]["event_type"] == "settlement.blocked"
    assert events[-1]["payload"]["escrowed_paise"] == 7_700_000


def test_seller_can_dispute_weighbridge_reading(client, clock, seller, buyer):
    lot_id = _award(client, clock, seller, buyer)
    _fund_and_deliver(client, clock, seller, buyer, lot_id, measured_grams=60_000)
    assert client.post(f"/lots/{lot_id}/delivery/accept", headers=buyer.headers).status_code == 403
    response = client.post(
        f"/lots/{lot_id}/delivery/dispute",
        headers=seller.headers,
        json={"reason": "slip shows the tare weight, not gross"},
    )
    assert response.json()["status"] == "disputed"


def test_only_winning_buyer_records_delivery(client, clock, register, seller, buyer):
    loser = register("buyer")
    lot_id = listed_lot(client, seller)
    bid(client, buyer, lot_id, 70_000)
    bid(client, loser, lot_id, 60_000)
    clock.advance(days=2)
    escrow = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()
    client.post(f"/payments/{escrow['intent_id']}/simulate-capture", headers=buyer.headers)
    client.post(
        f"/lots/{lot_id}/pickup",
        headers=seller.headers,
        json={"pickup_at": (clock.now + timedelta(hours=1)).isoformat()},
    )
    response = client.post(
        f"/lots/{lot_id}/delivery",
        headers=loser.headers,
        data={"measured_weight_grams": "1000"},
        files={"slip": SLIP},
    )
    assert response.status_code == 403


def test_pickup_must_be_in_the_future(client, clock, seller, buyer):
    lot_id = _award(client, clock, seller, buyer)
    escrow = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()
    client.post(f"/payments/{escrow['intent_id']}/simulate-capture", headers=buyer.headers)
    response = client.post(
        f"/lots/{lot_id}/pickup",
        headers=seller.headers,
        json={"pickup_at": (clock.now - timedelta(hours=1)).isoformat()},
    )
    assert response.status_code == 422


# --- payment deadline ------------------------------------------------------------------------


def _two_bids(client, clock, register, seller, buyer, *, reserve=None):
    """`buyer` wins at 70_000; a second buyer is runner-up at 65_000."""
    runner_up = register("buyer")
    lot_id = listed_lot(client, seller, reserve=reserve)
    assert bid(client, buyer, lot_id, 70_000).status_code == 200
    assert bid(client, runner_up, lot_id, 65_000).status_code == 200
    clock.advance(hours=25)
    lot = client.get(f"/lots/{lot_id}", headers=buyer.headers).json()
    assert lot["award"]["buyer"]["id"] == buyer.id
    assert _due(lot) == clock.now + timedelta(hours=24)
    return lot_id, runner_up


def _due(lot: dict) -> datetime:
    return datetime.fromisoformat(lot["award"]["escrow_due_at"])


def _events(client, seller, lot_id) -> list[dict]:
    return client.get(f"/lots/{lot_id}/custody", headers=seller.headers).json()


def test_unpaid_award_passes_to_the_next_bid(client, clock, register, seller, buyer):
    lot_id, runner_up = _two_bids(client, clock, register, seller, buyer)

    clock.advance(hours=23, minutes=59)
    assert (
        client.get(f"/lots/{lot_id}", headers=seller.headers).json()["award"]["buyer"]["id"]
        == buyer.id
    )

    clock.advance(minutes=1)
    lot = client.get(f"/lots/{lot_id}", headers=seller.headers).json()
    assert lot["status"] == "awarded"
    assert lot["award"]["buyer"]["id"] == runner_up.id
    assert lot["award"]["rate_paise_per_kg"] == 65_000  # the runner-up pays their own bid
    assert _due(lot) == clock.now + timedelta(hours=24)

    lapsed = client.get(f"/lots/{lot_id}", headers=buyer.headers).json()
    assert lapsed["award"] is None and lapsed["my_bid_lapsed"] is True
    assert client.get(f"/lots/{lot_id}", headers=runner_up.headers).json()["my_bid_lapsed"] is False
    # The lapsed winner can no longer start a payment.
    assert client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).status_code == 403

    event = _events(client, seller, lot_id)[-1]
    assert event["event_type"] == "award.lapsed"
    assert event["actor_id"] is None
    assert event["payload"]["reason"] == "not_paid"
    assert event["payload"]["lapsed_buyer_id"] == buyer.id
    assert event["payload"]["buyer_id"] == runner_up.id


def test_lot_ends_unsold_when_every_winner_lapses(client, clock, register, seller, buyer):
    lot_id, _ = _two_bids(client, clock, register, seller, buyer)
    clock.advance(hours=24)
    client.get("/lots", headers=seller.headers)  # the list view applies deadlines too
    clock.advance(hours=24)
    lot = client.get(f"/lots/{lot_id}", headers=seller.headers).json()
    assert lot["status"] == "unsold"
    assert lot["award"] is None
    assert [e["payload"]["result"] for e in _events(client, seller, lot_id)[-2:]] == [
        "awarded",
        "unsold",
    ]


def test_runner_up_below_reserve_does_not_win(client, clock, register, seller, buyer):
    lot_id, _ = _two_bids(client, clock, register, seller, buyer, reserve=68_000)
    clock.advance(hours=24)
    assert client.get(f"/lots/{lot_id}", headers=seller.headers).json()["status"] == "unsold"


def test_winner_can_decline_straight_away(client, clock, register, seller, buyer):
    lot_id, runner_up = _two_bids(client, clock, register, seller, buyer)
    for party in (seller, runner_up):
        assert client.post(f"/lots/{lot_id}/decline", headers=party.headers).status_code == 403

    lot = client.post(f"/lots/{lot_id}/decline", headers=buyer.headers).json()
    assert lot["award"] is None and lot["my_bid_lapsed"] is True
    assert client.post(f"/lots/{lot_id}/decline", headers=buyer.headers).status_code == 403

    lot = client.get(f"/lots/{lot_id}", headers=runner_up.headers).json()
    assert lot["award"]["buyer"]["id"] == runner_up.id
    event = _events(client, seller, lot_id)[-1]
    assert (event["payload"]["reason"], event["actor_id"]) == ("declined", buyer.id)


def test_payment_just_inside_the_deadline_funds_escrow(client, clock, register, seller, buyer):
    lot_id, _ = _two_bids(client, clock, register, seller, buyer)
    escrow = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()
    clock.advance(hours=23, minutes=59)
    client.post(f"/payments/{escrow['intent_id']}/simulate-capture", headers=buyer.headers)
    lot = client.get(f"/lots/{lot_id}", headers=seller.headers).json()
    assert lot["status"] == "funded"
    assert lot["award"]["escrow_due_at"] is None


def test_late_payment_goes_to_the_payers_wallet(client, clock, register, seller, buyer):
    lot_id, runner_up = _two_bids(client, clock, register, seller, buyer)
    escrow = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()
    clock.advance(hours=25)  # nobody looks at the lot until the payment lands

    response = client.post(
        f"/payments/{escrow['intent_id']}/simulate-capture", headers=buyer.headers
    )
    assert response.status_code == 200

    lot = client.get(f"/lots/{lot_id}", headers=seller.headers).json()
    assert lot["status"] == "awarded"
    assert lot["award"]["buyer"]["id"] == runner_up.id  # the late money didn't fund it
    wallet = client.get("/wallet", headers=buyer.headers).json()
    assert wallet["balance_paise"] == escrow["amount_paise"]
    assert [e["kind"] for e in wallet["entries"]] == ["late_payment_returned"]
    assert [e["event_type"] for e in _events(client, seller, lot_id)[-2:]] == [
        "award.lapsed",
        "payment.returned",
    ]


# --- Razorpay webhook ------------------------------------------------------------------------


class StubRazorpay(RazorpayGateway):
    """The real gateway with only the network call replaced, so signature checks are real."""

    def __init__(self):
        super().__init__("rzp_test_key", "rzp_test_secret")

    def create_order(self, amount_paise: int, receipt: str) -> str:
        return f"order_{receipt[:14]}"


def _webhook(client, payload: dict, secret: str = "whsec-test"):
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        "/payments/razorpay/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": signature},
    )


def _captured(order_id: str, amount: int, payment_id: str = "pay_123") -> dict:
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {"entity": {"id": payment_id, "order_id": order_id, "amount": amount}}
        },
    }


@pytest.mark.parametrize("gateway", [StubRazorpay()])
def test_razorpay_webhook_funds_escrow_once(client, clock, seller, buyer):
    lot_id = _award(client, clock, seller, buyer, grams=100_000, rate=70_000)
    escrow = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()
    assert escrow["gateway"] == "razorpay"
    assert escrow["razorpay_key_id"] == "rzp_test_key"
    order, amount = escrow["gateway_order_id"], escrow["amount_paise"]

    # Simulated capture is refused for real-rail intents.
    response = client.post(
        f"/payments/{escrow['intent_id']}/simulate-capture", headers=buyer.headers
    )
    assert response.status_code == 409

    assert _webhook(client, _captured(order, amount), secret="wrong").status_code == 400
    assert _webhook(client, _captured(order, amount - 1)).status_code == 409
    assert _webhook(client, _captured(order, amount)).json() == {"status": "captured"}
    assert _webhook(client, _captured(order, amount)).json() == {"status": "captured"}  # retry
    assert _webhook(client, _captured("order_elsewhere", 5)).json() == {"status": "unknown_order"}
    assert _webhook(client, {"event": "order.paid"}).json() == {"status": "ignored"}

    events = client.get(f"/lots/{lot_id}/custody", headers=seller.headers).json()
    assert [e["event_type"] for e in events].count("escrow.funded") == 1
    assert client.get(f"/lots/{lot_id}", headers=seller.headers).json()["status"] == "funded"


def _checkout_signature(order_id: str, payment_id: str, secret: str = "rzp_test_secret") -> str:
    body = f"{order_id}|{payment_id}".encode()
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.parametrize("gateway", [StubRazorpay()])
def test_razorpay_checkout_callback_funds_escrow(client, clock, register, seller, buyer):
    lot_id = _award(client, clock, seller, buyer)
    order = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()["gateway_order_id"]
    result = {
        "razorpay_order_id": order,
        "razorpay_payment_id": "pay_abc",
        "razorpay_signature": _checkout_signature(order, "pay_abc", secret="forged"),
    }
    assert (
        client.post("/payments/razorpay/verify", headers=buyer.headers, json=result).status_code
        == 400
    )

    result["razorpay_signature"] = _checkout_signature(order, "pay_abc")
    stranger = register("buyer")
    response = client.post("/payments/razorpay/verify", headers=stranger.headers, json=result)
    assert response.status_code == 404

    response = client.post("/payments/razorpay/verify", headers=buyer.headers, json=result)
    assert response.json()["status"] == "captured"
    # The webhook arriving later for the same payment changes nothing.
    amount = response.json()["amount_paise"]
    assert _webhook(client, _captured(order, amount, "pay_abc")).json() == {"status": "captured"}
    events = client.get(f"/lots/{lot_id}/custody", headers=seller.headers).json()
    assert [e["event_type"] for e in events].count("escrow.funded") == 1


@pytest.mark.parametrize("gateway", [StubRazorpay()])
def test_razorpay_webhook_after_decline_is_returned_not_retried(
    client, clock, register, seller, buyer
):
    lot_id, runner_up = _two_bids(client, clock, register, seller, buyer)
    escrow = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers).json()
    client.post(f"/lots/{lot_id}/decline", headers=buyer.headers)

    # Checkout was already open; Razorpay captures and tells us. Acknowledge it, don't 409.
    captured = _captured(escrow["gateway_order_id"], escrow["amount_paise"])
    assert _webhook(client, captured).json() == {"status": "captured"}
    assert _webhook(client, captured).json() == {"status": "captured"}  # retry: no double credit

    assert (
        client.get("/wallet", headers=buyer.headers).json()["balance_paise"]
        == escrow["amount_paise"]
    )
    lot = client.get(f"/lots/{lot_id}", headers=seller.headers).json()
    assert (lot["status"], lot["award"]["buyer"]["id"]) == ("awarded", runner_up.id)
