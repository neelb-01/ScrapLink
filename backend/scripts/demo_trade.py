"""Run one complete trade in-process and print what each party sees.

    python scripts/demo_trade.py [--pdf certificate.pdf]

Uses an in-memory database, a simulated payment rail and a clock the script can move forward,
so a 24-hour auction closes instantly. Nothing touches your .env or dev database.
"""

import argparse
import os
import sys
import tempfile
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from scraplink.app import create_app
from scraplink.classification import Suggestion
from scraplink.config import Settings
from scraplink.db import Base
from scraplink.kyc import gstin_check_char
from scraplink.models import KycStatus, Role, User
from scraplink.security import hash_password
from scraplink.seed import seed_materials

PASSWORD = "demo-password"


class Clock:
    now = datetime.now(UTC)

    def __call__(self):
        return self.now


class DemoClassifier:
    def classify(self, image, content_type):
        return Suggestion("copper", "A", 0.88)


def rupees(paise: int) -> str:
    return f"Rs {paise / 100:,.2f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", help="write the issued certificate here")
    args = parser.parse_args()

    clock = Clock()
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        jwt_secret=os.urandom(32).hex(),
        media_dir=tempfile.mkdtemp(prefix="scraplink-demo-"),
    )
    app = create_app(settings, clock=clock, classifier=DemoClassifier())
    Base.metadata.create_all(app.state.engine)
    with app.state.sessionmaker() as db:
        seed_materials(db, clock())
        db.add(
            User(
                phone="9000000000",
                name="Admin",
                password_hash=hash_password(PASSWORD),
                role=Role.ADMIN,
                kyc_status=KycStatus.APPROVED,
                created_at=clock(),
            )
        )
        db.commit()
    api = TestClient(app)

    def login(phone):
        token = api.post("/auth/login", json={"phone": phone, "password": PASSWORD})
        return {"Authorization": f"Bearer {token.json()['access_token']}"}

    admin = login("9000000000")

    def onboard(phone, name, role, business, pan=None):
        body = {"phone": phone, "password": PASSWORD, "name": name, "role": role}
        body["business_name"] = business
        if pan:
            base = f"32{pan}1Z"
            body["gstin"] = base + gstin_check_char(base)
        user = api.post("/auth/register", json=body).json()
        api.post(f"/admin/users/{user['id']}/kyc", headers=admin, json={"decision": "approve"})
        return login(phone)

    def step(title):
        print(f"\n== {title}")

    seller = onboard("9811111111", "Ravi", "seller", "Ravi Metal Traders, Kochi")
    agent = onboard("9822222222", "Anu", "agent", "ScrapLink field team")
    seller_id = api.get("/auth/me", headers=seller).json()["id"]
    buyer_a = onboard("9833333333", "Meera", "buyer", "Malabar Recyclers", pan="AAAPM1234C")
    buyer_b = onboard("9844444444", "Joseph", "buyer", "Periyar Non-Ferrous", pan="AAAPJ5678D")

    step("1. Field agent photographs the lot for the seller")
    photo = ("lot.jpg", b"\xff\xd8\xff\xe0" + os.urandom(2048), "image/jpeg")
    lot = api.post("/lots", headers=agent, files={"photo": photo}, data={"seller_id": seller_id})
    lot = lot.json()
    c = lot["classification"]
    print(
        f"   model suggests {c['suggested_material_code']} grade {c['suggested_grade']} "
        f"at {c['confidence']:.0%} confidence -> prefilled: {c['prefilled']}"
    )

    step("2. Seller-side confirms: copper, but grade B (painted), 180 kg")
    lot_id = lot["id"]
    est = api.post(
        f"/lots/{lot_id}/confirm",
        headers=agent,
        json={"material_code": "copper", "grade": "B", "declared_weight_grams": 180_000},
    ).json()["estimate"]
    print(
        f"   fair price {rupees(est['low_paise'])} - {rupees(est['high_paise'])} "
        f"(Rs {est['rate_paise_per_kg'] / 100:.2f}/kg)"
    )

    step("3. Listed for 24h sealed bids; two recyclers bid")
    api.post(f"/lots/{lot_id}/list", headers=seller, json={"auction_hours": 24})
    for who, rate in ((buyer_a, 57_000), (buyer_b, 58_750)):
        api.post(f"/lots/{lot_id}/bids", headers=who, json={"rate_paise_per_kg": rate})
    print("   bids placed: Rs 570.00/kg and Rs 587.50/kg (neither sees the other)")

    step("4. Clock moves past close; highest bid wins")
    clock.now += timedelta(hours=25)
    lot = api.get(f"/lots/{lot_id}", headers=seller).json()
    award = lot["award"]
    print(
        f"   {lot['status']}: {award['buyer']['business_name']} at "
        f"Rs {award['rate_paise_per_kg'] / 100:.2f}/kg; escrow due "
        f"{rupees(award['escrow_required_paise'])}"
    )

    step("5. Winner funds escrow (simulated rail)")
    intent = api.post(f"/lots/{lot_id}/escrow", headers=buyer_b).json()
    api.post(f"/payments/{intent['intent_id']}/simulate-capture", headers=buyer_b)
    print(f"   {rupees(intent['amount_paise'])} held in escrow")

    step("6. Pickup, weighbridge reads 176.4 kg")
    pickup = (clock.now + timedelta(hours=20)).isoformat()
    api.post(f"/lots/{lot_id}/pickup", headers=seller, json={"pickup_at": pickup})
    clock.now += timedelta(hours=21)
    slip = ("slip.jpg", b"\xff\xd8\xff\xe0" + os.urandom(1024), "image/jpeg")
    api.post(
        f"/lots/{lot_id}/delivery",
        headers=buyer_b,
        data={"measured_weight_grams": "176400"},
        files={"slip": slip},
    )

    step("7. Seller accepts the reading; escrow settles on measured weight")
    lot = api.post(f"/lots/{lot_id}/delivery/accept", headers=seller).json()
    seller_wallet = api.get("/wallet", headers=seller).json()["balance_paise"]
    buyer_wallet = api.get("/wallet", headers=buyer_b).json()["balance_paise"]
    print(
        f"   {lot['status']}: seller receives {rupees(seller_wallet)}, "
        f"buyer refunded {rupees(buyer_wallet)}"
    )

    step("8. Certificate")
    cert = api.get(f"/certificates/{lot['certificate_id']}", headers=seller).json()
    check = api.get(f"/certificates/{cert['id']}/verify").json()
    print(
        f"   {cert['event_count']} custody events, head {cert['head_hash'][:16]}..., "
        f"verifies: {check['valid']}"
    )
    if args.pdf:
        with open(args.pdf, "wb") as fh:
            fh.write(api.get(cert["pdf_url"], headers=seller).content)
        print(f"   PDF written to {args.pdf}")


if __name__ == "__main__":
    sys.exit(main())
