from datetime import timedelta

import pytest
from sqlalchemy import func, select

from scraplink import custody
from scraplink.anchoring import anchor_holds
from scraplink.demo import DEMO_PASSWORD, DemoAlreadyLoaded, seed_demo
from scraplink.models import CustodyAnchor, LedgerPosting, Lot
from scraplink.routing import IST
from scraplink.training_export import export_training_set


@pytest.fixture
def seeded(app, db, clock):
    summary = seed_demo(db, app.state.env.settings, app.state.env.storage, clock())
    db.commit()
    return summary


def _login(client, phone):
    response = client.post("/auth/login", json={"phone": phone, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_every_lot_state_is_represented(seeded):
    assert seeded.lots_by_status == {
        "awarded": 1,
        "delivered": 1,
        "disputed": 1,
        "draft": 1,
        "funded": 1,
        "listed": 5,
        "pickup_scheduled": 4,
        "settled": 8,
        "unsold": 1,
    }


def test_the_history_is_genuine(seeded, db):
    for lot_id in db.scalars(select(Lot.id)):
        check = custody.verify_chain(custody.lot_events(db, lot_id))
        assert check.valid, (lot_id, check.reason)
    assert db.scalar(select(func.sum(LedgerPosting.amount_paise))) == 0
    anchor = db.scalars(select(CustodyAnchor)).one()
    assert anchor_holds(db, anchor)


def test_screens_have_something_to_show(seeded, client, clock, admin):
    ravi, joseph, priya = (_login(client, p) for p in ("9000000001", "9000000011", "9000000013"))

    mine = client.get("/lots", headers=ravi).json()
    settled = next(lot for lot in mine if lot["status"] == "settled")
    invoice = client.get(f"/lots/{settled['id']}/invoice", headers=ravi).json()
    assert invoice["total_paise"] > invoice["taxable_paise"]

    assert client.get("/impact", headers=joseph).json()["trades"] == 4
    assert len(client.get("/rfqs", headers=ravi).json()) == 3  # the closed one is hidden
    statuses = sorted(a["status"] for a in client.get("/agreements", headers=ravi).json())
    assert statuses == ["active", "declined"]

    market = client.get("/lots?scope=market", headers=priya).json()
    batteries = next(m for m in market if m["material_code"] == "lead_acid_batteries")
    bid = client.post(
        f"/lots/{batteries['id']}/bids", headers=priya, json={"rate_paise_per_kg": 9_000}
    )
    assert bid.status_code == 403  # Priya holds no battery authorisation

    tomorrow = (clock().astimezone(IST) + timedelta(days=1)).date()
    route = client.get(f"/admin/routes?day={tomorrow}", headers=admin.headers).json()
    assert len(route["stops"]) == 3 and len(route["unplaced"]) == 1

    pending = client.get("/admin/users?kyc_status=pending", headers=admin.headers).json()
    assert {u["name"] for u in pending} == {"Suresh Pillai", "Meera Joseph"}


def test_copper_price_moved_with_the_market(seeded, client):
    history = client.get("/materials/copper/rates").json()
    assert [r["source"] for r in history] == ["market", "seed", "seed"]  # seed, back-dated copy
    assert history[0]["trade_count"] == 4  # the unpaid award doesn't count
    assert history[0]["rate_paise_per_kg"] > history[1]["rate_paise_per_kg"]


def test_demo_photos_never_reach_the_training_set(seeded, app, db, tmp_path):
    assert export_training_set(db, app.state.env.storage, tmp_path / "out").exported == 0


def test_loading_twice_is_refused(seeded, app, db, clock):
    with pytest.raises(DemoAlreadyLoaded):
        seed_demo(db, app.state.env.settings, app.state.env.storage, clock())
