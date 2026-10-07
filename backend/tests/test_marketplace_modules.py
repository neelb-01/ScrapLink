"""First slices of the catalogue breadth, compliance gating, RFQs and supply agreements."""

from datetime import timedelta

from helpers import bid, funded_lot, listed_lot


def test_catalogue_covers_non_metal_streams_with_metals_first(client):
    materials = client.get("/materials").json()["materials"]
    families = [m["family"] for m in materials]
    assert families[:5] == ["ferrous", "ferrous", "non_ferrous", "non_ferrous", "non_ferrous"]
    assert {"plastic", "paper", "e_waste", "battery"} <= set(families)
    regulated = {m["code"]: m["authorisation"] for m in materials if m["authorisation"]}
    assert regulated == {"e_waste_boards": "e_waste", "lead_acid_batteries": "battery"}


def test_e_waste_goes_only_to_authorised_recyclers(client, register, seller):
    lot_id = listed_lot(client, seller, material="e_waste_boards")
    lot = client.get(f"/lots/{lot_id}", headers=seller.headers).json()
    assert lot["material_authorisation"] == "e_waste"

    trader = register("buyer")
    response = bid(client, trader, lot_id, 15_000)
    assert response.status_code == 403
    assert "CPCB e-waste" in response.json()["detail"]

    recycler = register("buyer", authorisations=["e_waste"])
    assert client.get("/auth/me", headers=recycler.headers).json()["authorisations"] == ["e_waste"]
    assert bid(client, recycler, lot_id, 15_000).status_code == 200


def test_buyer_posts_a_request_and_sellers_see_it(client, clock, register, seller, buyer):
    needed_by = (clock.now + timedelta(days=7)).isoformat()
    body = {
        "material_code": "aluminium",
        "quantity_grams": 2_000_000,
        "target_rate_paise_per_kg": 15_500,
        "needed_by": needed_by,
        "note": "Extrusions preferred",
    }
    response = client.post("/rfqs", headers=buyer.headers, json=body)
    assert response.status_code == 201, response.text
    rfq = response.json()
    assert rfq["status"] == "open"
    assert rfq["material_name"] == "Aluminium"

    assert [r["id"] for r in client.get("/rfqs", headers=seller.headers).json()] == [rfq["id"]]
    assert client.get("/rfqs", headers=register("buyer").headers).json() == []
    assert client.post("/rfqs", headers=seller.headers, json=body).status_code == 403

    closed = client.post(f"/rfqs/{rfq['id']}/close", headers=buyer.headers).json()
    assert closed["status"] == "closed"
    assert client.get("/rfqs", headers=seller.headers).json() == []
    assert client.post(f"/rfqs/{rfq['id']}/close", headers=buyer.headers).status_code == 409


def test_requests_follow_the_same_compliance_and_date_rules(client, clock, buyer):
    base = {"quantity_grams": 500_000, "needed_by": (clock.now + timedelta(days=3)).isoformat()}
    response = client.post(
        "/rfqs", headers=buyer.headers, json={**base, "material_code": "lead_acid_batteries"}
    )
    assert response.status_code == 403
    past = {**base, "material_code": "copper", "needed_by": clock.now.isoformat()}
    assert client.post("/rfqs", headers=buyer.headers, json=past).status_code == 422


def test_supply_agreement_between_trading_partners(client, clock, register, seller, buyer):
    proposal = {
        "seller_id": seller.id,
        "material_code": "copper",
        "monthly_quantity_grams": 500_000,
        "rate_paise_per_kg": 66_000,
        "starts_on": "2026-11-01",
        "months": 6,
    }
    # No trade yet, so no standing to propose one.
    assert client.get("/agreements/partners", headers=buyer.headers).json() == []
    assert client.post("/agreements", headers=buyer.headers, json=proposal).status_code == 403

    funded_lot(client, clock, seller, buyer)
    partners = client.get("/agreements/partners", headers=buyer.headers).json()
    assert [p["id"] for p in partners] == [seller.id]

    response = client.post("/agreements", headers=buyer.headers, json=proposal)
    assert response.status_code == 201, response.text
    agreement = response.json()
    assert agreement["status"] == "proposed"
    assert [a["id"] for a in client.get("/agreements", headers=seller.headers).json()] == [
        agreement["id"]
    ]

    stranger = register("seller")
    url = f"/agreements/{agreement['id']}"
    assert client.post(f"{url}/accept", headers=stranger.headers).status_code == 404
    assert client.post(f"{url}/accept", headers=buyer.headers).status_code == 403
    accepted = client.post(f"{url}/accept", headers=seller.headers).json()
    assert accepted["status"] == "active"
    assert accepted["decided_at"] is not None
    assert client.post(f"{url}/decline", headers=seller.headers).status_code == 409
