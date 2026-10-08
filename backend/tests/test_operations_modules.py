"""First slices of invoicing, impact, logistics, route planning, anchoring and jobs."""

import hashlib
from datetime import timedelta

import pytest
from helpers import funded_lot, listed_lot, settled_lot, valid_gstin
from sqlalchemy import select

from scraplink.anchoring import merkle_root
from scraplink.models import CustodyEvent

KOCHI_NEAR = {"latitude": 10.0, "longitude": 76.3}  # about 2 km from the default depot
THRISSUR = {"latitude": 10.52, "longitude": 76.21}  # about 60 km


def test_draft_invoice_splits_gst_within_a_state(client, clock, register, admin):
    seller = register("seller", gstin=valid_gstin("AAAPS1234C"))  # Kerala, like the buyer
    buyer = register("buyer")
    lot = settled_lot(client, clock, seller, buyer, weighed=100_000)

    invoice = client.get(f"/lots/{lot['id']}/invoice", headers=buyer.headers).json()
    assert invoice["draft"] is True
    assert invoice["hsn"] == "7404"
    assert invoice["taxable_paise"] == 6_800_000  # 68_000 x 100 kg
    assert [(t["label"], t["percent"], t["amount_paise"]) for t in invoice["taxes"]] == [
        ("CGST", "9", 612_000),
        ("SGST", "9", 612_000),
    ]
    assert invoice["total_paise"] == 8_024_000
    assert invoice["reverse_charge"] is False

    outsider = register("buyer")
    assert client.get(f"/lots/{lot['id']}/invoice", headers=outsider.headers).status_code == 404


def test_unregistered_seller_invoice_is_reverse_charge(client, clock, seller, buyer):
    lot_id = funded_lot(client, clock, seller, buyer)
    assert client.get(f"/lots/{lot_id}/invoice", headers=buyer.headers).status_code == 409

    lot = settled_lot(client, clock, seller, buyer, weighed=50_000, material="brass")
    invoice = client.get(f"/lots/{lot['id']}/invoice", headers=seller.headers).json()
    assert [t["label"] for t in invoice["taxes"]] == ["IGST"]
    assert invoice["reverse_charge"] is True


def test_impact_counts_each_partys_settled_weight(client, clock, register, admin, seller, buyer):
    settled_lot(client, clock, seller, buyer, weighed=100_000)  # copper
    other = register("seller")
    settled_lot(client, clock, other, buyer, weighed=200_000, material="aluminium", grams=200_000)

    mine = client.get("/impact", headers=seller.headers).json()
    assert (mine["trades"], mine["weight_grams"], mine["co2e_avoided_grams"]) == (
        1,
        100_000,
        350_000,
    )
    bought = client.get("/impact", headers=buyer.headers).json()
    assert [m["code"] for m in bought["materials"]] == ["aluminium", "copper"]
    assert bought["co2e_avoided_grams"] == 350_000 + 1_800_000
    assert client.get("/impact", headers=admin.headers).json()["trades"] == 2


def test_transporters_are_admin_only(client, admin, seller):
    body = {"name": "Periyar Logistics", "phone": "9847012345", "vehicle": "Tata Ace"}
    body["capacity_grams"] = 750_000
    assert client.post("/admin/transporters", headers=seller.headers, json=body).status_code == 403
    response = client.post("/admin/transporters", headers=admin.headers, json=body)
    assert response.status_code == 201, response.text
    listed = client.get("/admin/transporters", headers=admin.headers).json()
    assert [t["name"] for t in listed] == ["Periyar Logistics"]


def test_route_visits_the_nearest_pickup_first(client, clock, register, admin, buyer):
    far, near, unknown = (funded_lot(client, clock, register("seller"), buyer) for _ in range(3))
    pickup_at = "2026-10-08T10:00:00+05:30"
    for lot_id, where in ((far, THRISSUR), (near, KOCHI_NEAR), (unknown, {})):
        response = client.post(
            f"/lots/{lot_id}/pickup",
            headers=buyer.headers,
            json={"pickup_at": pickup_at, **where},
        )
        assert response.status_code == 200, response.text

    lot = client.get(f"/lots/{near}", headers=buyer.headers).json()
    assert lot["pickup_location"] == KOCHI_NEAR

    route = client.get("/admin/routes?day=2026-10-08", headers=admin.headers).json()
    assert [s["lot_id"] for s in route["stops"]] == [near, far]
    assert [s["lot_id"] for s in route["unplaced"]] == [unknown]
    assert 1_000 < route["stops"][0]["leg_metres"] < 5_000
    assert (
        route["total_metres"]
        == sum(s["leg_metres"] for s in route["stops"]) + (route["return_metres"])
    )
    empty = client.get("/admin/routes?day=2026-10-09", headers=admin.headers).json()
    assert empty["stops"] == [] and empty["total_metres"] == 0


def test_pickup_location_needs_both_coordinates(client, clock, seller, buyer):
    lot_id = funded_lot(client, clock, seller, buyer)
    body = {"pickup_at": (clock.now + timedelta(days=1)).isoformat(), "latitude": 10.0}
    assert client.post(f"/lots/{lot_id}/pickup", headers=buyer.headers, json=body).status_code == (
        422
    )


def test_merkle_root_pairs_and_duplicates_odd_nodes():
    a, b, c = (hashlib.sha256(x).hexdigest() for x in (b"a", b"b", b"c"))
    pair = lambda x, y: hashlib.sha256(bytes.fromhex(x) + bytes.fromhex(y)).hexdigest()  # noqa: E731
    assert merkle_root([a]) == a
    assert merkle_root([a, b]) == pair(a, b)
    assert merkle_root([a, b, c]) == pair(pair(a, b), pair(c, c))
    with pytest.raises(ValueError):
        merkle_root([])


def test_anchor_seals_new_events_and_catches_tampering(client, db, clock, admin, seller, buyer):
    funded_lot(client, clock, seller, buyer)
    response = client.post("/admin/anchors", headers=admin.headers)
    assert response.status_code == 201, response.text
    anchor = response.json()
    assert anchor["event_count"] == db.query(CustodyEvent).count()
    assert client.post("/admin/anchors", headers=admin.headers).status_code == 409

    check = f"/admin/anchors/{anchor['id']}/check"
    assert client.get(check, headers=admin.headers).json()["holds"] is True

    event = db.scalars(select(CustodyEvent).order_by(CustodyEvent.id)).first()
    event.payload = {**event.payload, "photo_sha256": "0" * 64}
    db.commit()
    assert client.get(check, headers=admin.headers).json()["holds"] is False


def test_jobs_run_on_demand_and_record_the_run(client, clock, admin, seller, buyer):
    jobs = client.get("/admin/jobs", headers=admin.headers).json()
    assert [(j["name"], j["last_run"]) for j in jobs] == [
        ("close-auctions", None),
        ("anchor-custody", None),
        ("reprice", None),
    ]
    listed_lot(client, seller, hours=1)
    clock.advance(hours=2)
    run = client.post("/admin/jobs/close-auctions/run", headers=admin.headers).json()
    assert run["ok"] is True
    assert run["summary"] == "1 auctions closed, 0 unpaid awards passed on"

    jobs = client.get("/admin/jobs", headers=admin.headers).json()
    assert jobs[0]["last_run"]["summary"] == run["summary"]
    assert client.post("/admin/jobs/nope/run", headers=admin.headers).status_code == 404
    assert client.get("/admin/jobs", headers=seller.headers).status_code == 403


def test_worker_schedules_every_job():
    worker = pytest.importorskip("scraplink.worker", exc_type=ImportError)
    assert {job.name for job in worker.WorkerSettings.cron_jobs} == {
        "close-auctions",
        "anchor-custody",
        "reprice",
    }
