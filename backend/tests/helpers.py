import os
from dataclasses import dataclass

from fastapi.testclient import TestClient

from scraplink.kyc import gstin_check_char

PHOTO = ("lot.jpg", b"\xff\xd8\xff\xe0" + os.urandom(256), "image/jpeg")
SLIP = ("slip.jpg", b"\xff\xd8\xff\xe0" + os.urandom(256), "image/jpeg")


def valid_gstin(pan: str, state: str = "32") -> str:
    base = f"{state}{pan}1Z"
    return base + gstin_check_char(base)


@dataclass
class Party:
    id: str
    headers: dict


def create_lot(client: TestClient, party: Party) -> dict:
    response = client.post("/lots", headers=party.headers, files={"photo": PHOTO})
    assert response.status_code == 201, response.text
    return response.json()


def listed_lot(
    client: TestClient,
    seller: Party,
    *,
    material: str = "copper",
    grade: str = "A",
    grams: int = 100_000,
    hours: int = 24,
    reserve: int | None = None,
) -> str:
    lot_id = create_lot(client, seller)["id"]
    response = client.post(
        f"/lots/{lot_id}/confirm",
        headers=seller.headers,
        json={"material_code": material, "grade": grade, "declared_weight_grams": grams},
    )
    assert response.status_code == 200, response.text
    response = client.post(
        f"/lots/{lot_id}/list",
        headers=seller.headers,
        json={"auction_hours": hours, "reserve_rate_paise_per_kg": reserve},
    )
    assert response.status_code == 200, response.text
    return lot_id


def bid(client: TestClient, buyer: Party, lot_id: str, rate: int):
    return client.post(
        f"/lots/{lot_id}/bids", headers=buyer.headers, json={"rate_paise_per_kg": rate}
    )
