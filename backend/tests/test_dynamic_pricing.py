"""Dynamic pricing: reference prices follow what recent paid trades were worth."""

from decimal import Decimal

from helpers import bid, create_lot, listed_lot

from scraplink import pricing

COPPER = 68_000  # the seeded grade A price, paise per kg


def paid_trade(client, clock, seller, buyer, rate: int, *, grade: str = "A", pay: bool = True):
    """A copper lot won by `buyer` at `rate`, paid into escrow unless `pay` is False."""
    lot_id = listed_lot(client, seller, grade=grade)
    assert bid(client, buyer, lot_id, rate).status_code == 200
    clock.advance(hours=25)
    if pay:
        escrow = client.post(f"/lots/{lot_id}/escrow", headers=buyer.headers)
        assert escrow.status_code == 200, escrow.text
        capture = client.post(
            f"/payments/{escrow.json()['intent_id']}/simulate-capture", headers=buyer.headers
        )
        assert capture.status_code == 200, capture.text
    return lot_id


def reprice(client, admin) -> str:
    run = client.post("/admin/jobs/reprice/run", headers=admin.headers).json()
    assert run["ok"] is True, run
    return run["summary"]


def copper(client) -> dict:
    materials = client.get("/materials").json()["materials"]
    return next(m for m in materials if m["code"] == "copper")


def test_market_move_goes_part_way_toward_the_median_and_is_capped():
    move = pricing.market_move(
        68_000, [70_000, 74_000, 72_000], blend=Decimal("0.5"), max_step=Decimal("0.10")
    )
    assert move == pricing.MarketMove(
        median_paise_per_kg=72_000, rate_paise_per_kg=70_000, capped=False
    )

    one_odd_trade = pricing.market_move(
        68_000, [69_000, 69_000, 500_000], blend=Decimal("0.5"), max_step=Decimal("0.10")
    )
    assert one_odd_trade.rate_paise_per_kg == 68_500

    falling = pricing.market_move(
        68_000, [40_000] * 3, blend=Decimal("0.5"), max_step=Decimal("0.10")
    )
    assert (falling.rate_paise_per_kg, falling.capped) == (61_200, True)

    assert pricing.median([1, 2, 3, 4]) == 3  # 2.5, rounded half up
    assert pricing.grade_a_equivalent(57_800, "B") == 68_000
    assert pricing.grade_a_equivalent(67_184, "A", 120) == 68_000  # 1.2% freight allowance


def test_paid_trades_move_the_price_and_explain_why(client, clock, admin, seller, buyer):
    paid_trade(client, clock, seller, buyer, 70_000)
    paid_trade(client, clock, seller, buyer, 74_000)
    paid_trade(client, clock, seller, buyer, 61_200, grade="B")  # 72,000 at grade A

    assert reprice(client, admin) == "Copper ₹680→₹700 on 3 trades; 12 held"

    rate = copper(client)["rate"]
    assert rate["rate_paise_per_kg"] == 70_000
    assert rate["source"] == "market"
    assert rate["previous_rate_paise_per_kg"] == COPPER
    assert (rate["trade_count"], rate["window_days"]) == (3, 30)
    assert rate["market_median_paise_per_kg"] == 72_000
    assert rate["capped"] is False

    history = client.get("/materials/copper/rates").json()
    assert [(r["rate_paise_per_kg"], r["source"]) for r in history] == [
        (70_000, "market"),
        (COPPER, "seed"),
    ]

    # The next lot is valued at the new price, and carries the reason with it.
    lot_id = create_lot(client, seller)["id"]
    confirmed = client.post(
        f"/lots/{lot_id}/confirm",
        headers=seller.headers,
        json={"material_code": "copper", "grade": "A", "declared_weight_grams": 100_000},
    ).json()
    assert confirmed["estimate"]["rate_paise_per_kg"] == 70_000
    assert confirmed["estimate"]["reference_rate"]["source"] == "market"

    # The same trades don't push it further than their median on later runs.
    for _ in range(5):
        reprice(client, admin)
    assert copper(client)["rate"]["rate_paise_per_kg"] <= 72_000


def test_too_few_paid_trades_hold_the_price(client, clock, admin, seller, buyer):
    paid_trade(client, clock, seller, buyer, 80_000)
    paid_trade(client, clock, seller, buyer, 80_000)
    paid_trade(client, clock, seller, buyer, 80_000, pay=False)  # won but never paid

    assert reprice(client, admin) == "no prices moved (13 held)"
    assert copper(client)["rate"]["source"] == "seed"


def test_one_run_moves_at_most_the_cap(client, clock, admin, seller, buyer):
    for _ in range(3):
        paid_trade(client, clock, seller, buyer, 90_000)
    reprice(client, admin)
    rate = copper(client)["rate"]
    assert (rate["rate_paise_per_kg"], rate["capped"]) == (74_800, True)


def test_old_trades_and_trades_before_an_admin_price_dont_count(
    client, clock, admin, seller, buyer
):
    for _ in range(3):
        paid_trade(client, clock, seller, buyer, 75_000)
    response = client.put(
        "/admin/materials/copper/rate", headers=admin.headers, json={"rate_paise_per_kg": 69_000}
    )
    assert response.json()["rate"]["source"] == "admin"
    assert response.json()["rate"]["previous_rate_paise_per_kg"] == COPPER
    clock.advance(hours=1)
    reprice(client, admin)
    assert copper(client)["rate"]["rate_paise_per_kg"] == 69_000

    for _ in range(3):
        paid_trade(client, clock, seller, buyer, 73_000)
    clock.advance(days=31)
    reprice(client, admin)
    assert copper(client)["rate"]["rate_paise_per_kg"] == 69_000


def test_catalogue_states_the_pricing_rule(client):
    assert client.get("/materials").json()["pricing_rule"] == {
        "window_days": 30,
        "min_trades": 3,
        "blend_percent": 50,
        "max_step_percent": 10,
    }
