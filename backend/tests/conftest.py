import itertools
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from helpers import Party, valid_gstin

from scraplink.app import create_app
from scraplink.config import Settings
from scraplink.db import Base
from scraplink.models import KycStatus, Role, User
from scraplink.security import hash_password
from scraplink.seed import seed_materials

PASSWORD = "correct-horse-battery"


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta) -> None:
        self.now += timedelta(**delta)


class StubClassifier:
    def __init__(self):
        self.next = None

    def classify(self, image, content_type):
        return self.next


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def classifier() -> StubClassifier:
    return StubClassifier()


@pytest.fixture
def gateway():
    """None means the settings default (simulated). Tests override to exercise Razorpay."""
    return None


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        # Set TEST_DATABASE_URL to run the suite against PostgreSQL (tables are dropped after
        # each test, so point it at a throwaway database).
        database_url=os.environ.get("TEST_DATABASE_URL", "sqlite://"),
        jwt_secret="test-secret-that-is-at-least-32-bytes-long",
        media_dir=str(tmp_path / "media"),
        public_base_url="https://scraplink.test",
        razorpay_webhook_secret="whsec-test",
    )


@pytest.fixture
def app(settings, clock, classifier, gateway):
    app = create_app(settings, clock=clock, classifier=classifier, gateway=gateway)
    Base.metadata.create_all(app.state.engine)
    with app.state.sessionmaker() as db:
        seed_materials(db, clock())
        db.commit()
    yield app
    Base.metadata.drop_all(app.state.engine)
    app.state.engine.dispose()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def db(app):
    with app.state.sessionmaker() as session:
        yield session


def _login(client: TestClient, phone: str) -> dict:
    response = client.post("/auth/login", json={"phone": phone, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin(app, client) -> Party:
    with app.state.sessionmaker() as session:
        user = User(
            phone="9999999999",
            name="Platform admin",
            password_hash=hash_password(PASSWORD),
            role=Role.ADMIN,
            kyc_status=KycStatus.APPROVED,
            created_at=datetime.now(UTC),
        )
        session.add(user)
        session.commit()
        return Party(str(user.id), _login(client, user.phone))


@pytest.fixture
def register(client, admin):
    """Register through the API, approve KYC as admin, and sign in."""
    counter = itertools.count(1)

    def _register(
        role: str, *, approve: bool = True, authorisations: list[str] | None = None, **fields
    ) -> Party:
        n = next(counter)
        phone = f"98{n:08d}"
        if role == "buyer" and "gstin" not in fields:
            fields["gstin"] = valid_gstin(f"AAAPB{n:04d}C")
        body = {"phone": phone, "password": PASSWORD, "name": f"{role} {n}", "role": role, **fields}
        response = client.post("/auth/register", json=body)
        assert response.status_code == 201, response.text
        user_id = response.json()["id"]
        if approve:
            decision = {"decision": "approve", "authorisations": authorisations or []}
            response = client.post(
                f"/admin/users/{user_id}/kyc", headers=admin.headers, json=decision
            )
            assert response.status_code == 200, response.text
        return Party(user_id, _login(client, phone))

    return _register


@pytest.fixture
def seller(register) -> Party:
    return register("seller", business_name="Kochi Metal Traders")


@pytest.fixture
def buyer(register) -> Party:
    return register("buyer", business_name="Malabar Recycling Pvt Ltd")
