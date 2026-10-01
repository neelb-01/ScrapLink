import pytest
from helpers import PHOTO, create_lot, valid_gstin

from scraplink.classification import Suggestion


@pytest.mark.parametrize(
    "suggestion",
    [
        Suggestion("copper", "A", 0.74),  # just under the 0.75 threshold
        Suggestion("titanium", "A", 0.99),  # confident, but not a material we trade
        None,  # ML service down or unconfigured
    ],
)
def test_suggestion_is_not_prefilled_unless_confident_and_known(
    client, classifier, seller, suggestion
):
    classifier.next = suggestion
    lot = create_lot(client, seller)
    assert lot["classification"]["prefilled"] is False
    # Capture still works: the seller picks by hand.
    response = client.post(
        f"/lots/{lot['id']}/confirm",
        headers=seller.headers,
        json={"material_code": "aluminium", "grade": "A", "declared_weight_grams": 40_000},
    )
    assert response.status_code == 200
    assert response.json()["estimate"]["total_paise"] == 640_000  # 16_000 x 40 kg


def test_raw_suggestion_is_kept_even_when_below_threshold(client, classifier, seller):
    classifier.next = Suggestion("brass", None, 0.42)
    lot = create_lot(client, seller)
    assert lot["classification"]["suggested_material_code"] == "brass"
    assert lot["classification"]["confidence"] == 0.42


def test_unapproved_seller_cannot_create_lots(client, register):
    pending = register("seller", approve=False)
    response = client.post("/lots", headers=pending.headers, files={"photo": PHOTO})
    assert response.status_code == 403
    assert "KYC" in response.json()["detail"]


def test_non_image_upload_is_rejected(client, seller):
    response = client.post(
        "/lots", headers=seller.headers, files={"photo": ("x.pdf", b"%PDF-1.4", "application/pdf")}
    )
    assert response.status_code == 422


def test_agent_captures_on_behalf_of_seller(client, db, register, seller):
    agent = register("agent")
    assert client.post("/lots", headers=agent.headers, files={"photo": PHOTO}).status_code == 422

    lot = create_lot(client, agent, seller_id=seller.id)
    assert lot["seller"]["id"] == seller.id
    assert lot["captured_by_id"] == agent.id

    # The agent can finish the listing, and the seller sees it as theirs.
    response = client.post(
        f"/lots/{lot['id']}/confirm",
        headers=agent.headers,
        json={"material_code": "steel_hms", "grade": "C", "declared_weight_grams": 1_200_000},
    )
    assert response.status_code == 200
    mine = client.get("/lots", headers=seller.headers).json()
    assert [m["id"] for m in mine] == [lot["id"]]

    created = client.get(f"/lots/{lot['id']}/custody", headers=seller.headers).json()[0]
    assert created["actor_id"] == agent.id
    assert created["payload"]["seller_id"] == seller.id


def test_agent_cannot_capture_for_a_buyer(client, register, buyer):
    agent = register("agent")
    response = client.post(
        "/lots", headers=agent.headers, files={"photo": PHOTO}, data={"seller_id": buyer.id}
    )
    assert response.status_code == 404


def test_seller_cannot_capture_for_someone_else(client, register, seller):
    other = register("seller")
    response = client.post(
        "/lots", headers=seller.headers, files={"photo": PHOTO}, data={"seller_id": other.id}
    )
    assert response.status_code == 403


def test_buyer_must_register_with_valid_gstin(client):
    base = {"phone": "9812345678", "password": "long-enough-pw", "name": "B", "role": "buyer"}
    assert client.post("/auth/register", json=base).status_code == 422

    gstin = valid_gstin("ABCDE1234F")
    typo = gstin[:-1] + ("A" if gstin[-1] != "A" else "B")
    response = client.post("/auth/register", json={**base, "gstin": typo})
    assert response.status_code == 422
    assert "check character" in response.json()["detail"]

    response = client.post("/auth/register", json={**base, "gstin": gstin.lower()})
    assert response.status_code == 201
    assert response.json()["gstin"] == gstin
    assert response.json()["pan"] == "ABCDE1234F"  # derived from the GSTIN
    assert response.json()["kyc_status"] == "pending"


def test_pan_must_match_gstin(client):
    response = client.post(
        "/auth/register",
        json={
            "phone": "9812345679",
            "password": "long-enough-pw",
            "name": "S",
            "role": "seller",
            "gstin": valid_gstin("ABCDE1234F"),
            "pan": "ZZZZZ9999Z",
        },
    )
    assert response.status_code == 422


def test_duplicate_phone_is_rejected(client, register):
    register("seller")
    body = {"phone": "9800000001", "password": "long-enough-pw", "name": "x", "role": "seller"}
    assert client.post("/auth/register", json=body).status_code == 409


def test_wrong_password_and_missing_token(client, seller):
    bad = client.post("/auth/login", json={"phone": "9800000001", "password": "nope-nope-nope"})
    assert bad.status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_admin_endpoints_are_admin_only(client, seller):
    assert client.get("/admin/users", headers=seller.headers).status_code == 403


def test_admin_rate_change_applies_to_new_confirmations(client, admin, clock, seller):
    response = client.put(
        "/admin/materials/copper/rate", headers=admin.headers, json={"rate_paise_per_kg": 70_000}
    )
    assert response.json()["reference_rate_paise_per_kg"] == 70_000
    catalogue = client.get("/materials").json()  # public
    copper = next(m for m in catalogue["materials"] if m["code"] == "copper")
    assert copper["reference_rate_paise_per_kg"] == 70_000
    assert [g["code"] for g in catalogue["grades"]] == ["A", "B", "C"]


def test_agent_looks_up_seller_by_phone(client, register, seller):
    agent = register("agent")
    found = client.get("/sellers/lookup", params={"phone": "9800000001"}, headers=agent.headers)
    assert found.status_code == 200
    assert found.json()["id"] == seller.id
    assert found.json()["kyc_status"] == "approved"

    missing = client.get("/sellers/lookup", params={"phone": "9811110000"}, headers=agent.headers)
    assert missing.status_code == 404
    as_seller = client.get(
        "/sellers/lookup", params={"phone": "9800000001"}, headers=seller.headers
    )
    assert as_seller.status_code == 403
