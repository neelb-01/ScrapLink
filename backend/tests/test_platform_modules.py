"""Small demonstrable slices: profiles and KYC documents, lot location and pickup date, grade
hints, market filters, open auctions, transport, numbered invoices, ESG export, notifications,
categories and the admin overview."""

import re
from datetime import timedelta

from helpers import bid, create_lot, funded_lot, listed_lot, settled_lot

from scraplink.classification import Suggestion

PDF = ("licence.pdf", b"%PDF-1.4 test document", "application/pdf")


def confirm(client, seller, lot_id, **extra):
    body = {"material_code": "copper", "grade": "A", "declared_weight_grams": 100_000, **extra}
    return client.post(f"/lots/{lot_id}/confirm", headers=seller.headers, json=body)


def texts(client, party) -> list[str]:
    return [n["text"] for n in client.get("/notifications", headers=party.headers).json()["items"]]


# --- 1. users and KYC ----------------------------------------------------------------------


def test_profile_and_kyc_document_reach_the_admin(client, app, register, admin):
    seller = register("seller", approve=False, email="ravi@example.com", place="thrissur")
    me = client.get("/auth/me", headers=seller.headers).json()
    assert (me["email"], me["place"], me["kyc_document_name"]) == (
        "ravi@example.com",
        "thrissur",
        None,
    )

    changed = client.patch(
        "/auth/me", headers=seller.headers, json={"business_name": "Ravi Metals", "place": "kochi"}
    ).json()
    assert (changed["business_name"], changed["place"], changed["email"]) == (
        "Ravi Metals",
        "kochi",
        "ravi@example.com",  # left out, so unchanged
    )
    bad = client.patch("/auth/me", headers=seller.headers, json={"place": "atlantis"})
    assert bad.status_code == 422

    upload = client.post("/auth/me/kyc-document", headers=seller.headers, files={"document": PDF})
    assert upload.json()["kyc_document_name"] == "licence.pdf"
    document = client.get(f"/admin/users/{seller.id}/kyc-document", headers=admin.headers)
    assert (document.status_code, document.content) == (200, PDF[1])
    assert document.headers["content-type"] == "application/pdf"
    assert (
        client.get(f"/admin/users/{seller.id}/kyc-document", headers=seller.headers).status_code
        == 403
    )

    decision = {"decision": "approve", "authorisations": []}
    client.post(f"/admin/users/{seller.id}/kyc", headers=admin.headers, json=decision)
    assert texts(client, seller) == [
        "Your account is approved. You can start trading on ScrapLink."
    ]
    sent = app.state.env.mailer.sent
    assert sent[-1][0] == "ravi@example.com"  # emailed as well, through the logging mailer


# --- 2 and 4. lot location, pickup date, and location in the estimate -----------------------


def test_location_and_pickup_date_shape_the_estimate(client, clock, seller):
    places = client.get("/places").json()
    assert places[0]["code"] == "kochi" and places[0]["location_adjustment_bp"] == 0
    thrissur = next(p for p in places if p["code"] == "thrissur")
    assert 50 <= thrissur["km_from_yard"] <= 70

    lot_id = create_lot(client, seller)["id"]
    yesterday = (clock.now - timedelta(days=1)).date().isoformat()
    assert (
        confirm(client, seller, lot_id, place="thrissur", pickup_ready_on=yesterday).status_code
        == 422
    )

    ready = (clock.now + timedelta(days=2)).date().isoformat()
    lot = confirm(client, seller, lot_id, place="thrissur", pickup_ready_on=ready).json()
    assert (lot["place_name"], lot["pickup_ready_on"]) == ("Thrissur", ready)
    estimate = lot["estimate"]
    assert estimate["location_adjustment_bp"] == thrissur["location_adjustment_bp"]
    expected = round(68_000 * (10_000 - thrissur["location_adjustment_bp"]) / 10_000)
    assert estimate["rate_paise_per_kg"] == expected


# --- 3. grade suggestions --------------------------------------------------------------------


def test_confident_grade_is_prefilled_and_a_weak_one_is_a_hint(client, classifier, seller):
    classifier.next = Suggestion("copper", "B", 0.9, grade_confidence=0.81)
    assert create_lot(client, seller)["classification"]["grade_prefilled"] is True
    classifier.next = Suggestion("copper", "B", 0.9, grade_confidence=0.4)
    weak = create_lot(client, seller)["classification"]
    assert (weak["suggested_grade"], weak["grade_prefilled"]) == ("B", False)


def test_new_streams_are_in_the_catalogue(client):
    materials = {m["code"]: m["family"] for m in client.get("/materials").json()["materials"]}
    assert materials["glass_cullet"] == "glass"
    assert materials["textile_waste"] == "textile"
    assert materials["organic_waste"] == "organic"


# --- 5. marketplace: filters, open bidding, award by the seller ----------------------------


def test_market_filters_by_stream_and_place(client, seller, buyer):
    for material, place in (("copper", "kochi"), ("occ_cardboard", "thrissur")):
        lot_id = create_lot(client, seller)["id"]
        body = {"material_code": material, "grade": "A", "declared_weight_grams": 50_000}
        client.post(f"/lots/{lot_id}/confirm", headers=seller.headers, json=body | {"place": place})
        client.post(f"/lots/{lot_id}/list", headers=seller.headers, json={"auction_hours": 24})

    def market(**query):
        found = client.get("/lots", headers=buyer.headers, params={"scope": "market", **query})
        return [lot["material_code"] for lot in found.json()]

    assert sorted(market()) == ["copper", "occ_cardboard"]
    assert market(family="paper") == ["occ_cardboard"]
    assert market(place="kochi") == ["copper"]


def test_open_auction_shows_the_best_bid_and_the_seller_can_accept(client, clock, register, seller):
    first, second = register("buyer"), register("buyer")
    lot_id = create_lot(client, seller)["id"]
    confirm(client, seller, lot_id)
    listing = client.post(
        f"/lots/{lot_id}/list",
        headers=seller.headers,
        json={"auction_hours": 24, "auction_format": "open"},
    ).json()
    assert listing["auction_format"] == "open"

    assert bid(client, first, lot_id, 70_000).status_code == 200
    too_low = bid(client, second, lot_id, 70_050)
    assert too_low.status_code == 422 and "₹701" in too_low.json()["detail"]
    assert bid(client, second, lot_id, 70_100).status_code == 200

    seen = client.get(f"/lots/{lot_id}", headers=first.headers).json()
    assert seen["best_bid_rate_paise_per_kg"] == 70_100
    assert "You've been outbid" in texts(client, first)[0]

    bids = client.get(f"/lots/{lot_id}/bids", headers=seller.headers).json()
    assert [b["rate_paise_per_kg"] for b in bids] == [70_100, 70_000]
    chosen = next(b for b in bids if b["rate_paise_per_kg"] == 70_000)
    accepted = client.post(
        f"/lots/{lot_id}/accept", headers=seller.headers, json={"bid_id": chosen["id"]}
    ).json()
    assert accepted["status"] == "awarded"
    assert accepted["award"]["rate_paise_per_kg"] == 70_000
    assert texts(client, first)[0].startswith("You won the copper lot at ₹700/kg")


def test_sealed_auction_keeps_bids_hidden_and_cannot_be_accepted_early(client, seller, buyer):
    lot_id = listed_lot(client, seller)
    bid(client, buyer, lot_id, 70_000)
    assert (
        client.get(f"/lots/{lot_id}", headers=buyer.headers).json()["best_bid_rate_paise_per_kg"]
        is None
    )
    assert client.get(f"/lots/{lot_id}/bids", headers=seller.headers).json() == []
    early = client.post(f"/lots/{lot_id}/accept", headers=seller.headers, json={"bid_id": 1})
    assert early.status_code == 409
    assert texts(client, seller)[0] == (
        "A buyer bid on your copper lot. Bids stay sealed until bidding closes."
    )


# --- 6. pickup: transporter and weight at pickup --------------------------------------------


def test_transporter_is_assigned_and_pickup_weight_recorded(client, clock, admin, seller, buyer):
    lot_id = funded_lot(client, clock, seller, buyer)
    body = {"name": "Periyar Logistics", "phone": "9847012345", "vehicle": "Tata Ace"}
    truck = client.post(
        "/admin/transporters", headers=admin.headers, json=body | {"capacity_grams": 750_000}
    ).json()
    assign = {"transporter_id": truck["id"]}
    assert (
        client.post(f"/lots/{lot_id}/transporter", headers=seller.headers, json=assign).status_code
        == 403
    )
    lot = client.post(f"/lots/{lot_id}/transporter", headers=admin.headers, json=assign).json()
    assert lot["transporter"]["name"] == "Periyar Logistics"

    pickup_at = clock.now + timedelta(days=1)
    client.post(
        f"/lots/{lot_id}/pickup",
        headers=seller.headers,
        json={"pickup_at": pickup_at.isoformat(), "latitude": 10.0, "longitude": 76.3},
    )
    weighed = client.post(
        f"/lots/{lot_id}/pickup-weight", headers=seller.headers, json={"weight_grams": 98_500}
    )
    assert weighed.json()["pickup_weight_grams"] == 98_500
    assert texts(client, buyer)[0] == "The seller weighed 98.5 kg as the copper lot was loaded."

    day = (pickup_at + timedelta(hours=5, minutes=30)).date().isoformat()
    route = client.get(f"/admin/routes?day={day}", headers=admin.headers).json()
    assert route["stops"][0]["transporter_name"] == "Periyar Logistics"


# --- 7. invoices -----------------------------------------------------------------------------


def test_settlement_numbers_each_invoice_in_turn(client, clock, register, seller, buyer):
    first = settled_lot(client, clock, seller, buyer, weighed=100_000)
    second = settled_lot(client, clock, seller, buyer, weighed=100_000)
    numbers = [
        client.get(f"/lots/{lot['id']}/invoice", headers=buyer.headers).json()["number"]
        for lot in (first, second)
    ]
    assert numbers == ["INV/2026-27/0001", "INV/2026-27/0002"]
    assert first["invoice_number"] == "INV/2026-27/0001"
    assert any("Invoice INV/2026-27/0001" in t for t in texts(client, seller))


# --- 9. ESG and analytics --------------------------------------------------------------------


def test_impact_counts_value_and_exports_csv(client, clock, seller, buyer):
    settled_lot(client, clock, seller, buyer, weighed=100_000)
    report = client.get("/impact", headers=seller.headers).json()
    assert report["value_paise"] == 6_800_000  # ₹680 x 100 kg: the seller's revenue
    csv = client.get("/impact.csv", headers=buyer.headers)
    assert csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines() == [
        "material,trades,weight_kg,co2e_avoided_kg,value_inr",
        '"Copper",1,100.000,350.000,68000.00',
        '"Total",1,100.000,350.000,68000.00',
    ]


# --- 10. administration and notifications ---------------------------------------------------


def test_notifications_are_listed_counted_and_marked_read(client, clock, seller, buyer):
    lot_id = listed_lot(client, seller, hours=1)
    bid(client, buyer, lot_id, 69_000)
    clock.advance(hours=2)
    client.get(f"/lots/{lot_id}", headers=buyer.headers)  # closes the auction

    inbox = client.get("/notifications", headers=buyer.headers).json()
    assert inbox["unread"] == 2  # the win, and the earlier account approval
    assert re.match(
        r"You won the copper lot at ₹690/kg\. Pay ₹75,900 into escrow by ",
        inbox["items"][0]["text"],
    )
    assert inbox["items"][0]["lot_id"] == lot_id
    assert client.post("/notifications/read", headers=buyer.headers).json()["unread"] == 0
    seller_inbox = texts(client, seller)
    assert seller_inbox[0].startswith("Your copper lot went to ")


def test_admin_adds_a_category_with_its_starting_price(client, admin, seller):
    body = {
        "code": "ms_turnings",
        "name": "MS turnings",
        "family": "ferrous",
        "description": "Mild steel lathe turnings",
        "rate_paise_per_kg": 2_600,
    }
    assert client.post("/admin/materials", headers=seller.headers, json=body).status_code == 403
    created = client.post("/admin/materials", headers=admin.headers, json=body)
    assert created.status_code == 201, created.text
    assert created.json()["rate"]["source"] == "admin"
    assert client.post("/admin/materials", headers=admin.headers, json=body).status_code == 409
    wrong = client.post(
        "/admin/materials", headers=admin.headers, json=body | {"code": "x_y", "family": "gold"}
    )
    assert wrong.status_code == 422
    codes = [m["code"] for m in client.get("/materials").json()["materials"]]
    assert "ms_turnings" in codes


def test_overview_counts_people_lots_money_and_services(client, clock, admin, seller, buyer):
    settled_lot(client, clock, seller, buyer, weighed=100_000)
    view = client.get("/admin/overview", headers=admin.headers).json()
    assert {"name": "seller (approved)", "count": 1} in view["users"]
    assert {"name": "settled", "count": 1} in view["lots"]
    assert view["traded_paise"] == 6_800_000
    assert view["escrow_held_paise"] == 0  # settled, so nothing is left in escrow
    assert view["notifications_sent"] > 0
    assert view["ml"] == {"configured": False, "reachable": False, "model": None}
    assert [j["name"] for j in view["jobs"]] == ["close-auctions", "anchor-custody", "reprice"]
    assert client.get("/admin/overview", headers=seller.headers).status_code == 403
