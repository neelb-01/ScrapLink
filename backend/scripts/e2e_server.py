"""Backend for browser end-to-end tests.

    python scripts/e2e_server.py --port 8010 --data ./e2e-data

Fresh SQLite database and media directory on every start, seeded catalogue, an admin
(phone 9999900000, password e2e-admin-pass), a simulated payment rail, and a clock tests can
move forward with POST /__e2e__/advance {"hours": 25}. That route exists only in this script —
the application itself has no way to change its clock.
"""

import argparse
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import uvicorn
from pydantic import BaseModel

from scraplink.app import create_app
from scraplink.classification import Suggestion, classifier_from_url
from scraplink.config import Settings
from scraplink.db import Base
from scraplink.models import KycStatus, Role, User
from scraplink.payments import SimulatedGateway
from scraplink.security import hash_password
from scraplink.seed import seed_materials

ADMIN_PHONE, ADMIN_PASSWORD = "9999900000", "e2e-admin-pass"


class Clock:
    def __init__(self):
        self.now = datetime.now(UTC)

    def __call__(self) -> datetime:
        return self.now


class FixedClassifier:
    """Every photo looks like confident copper, so the prefill path is exercised."""

    def classify(self, image: bytes, content_type: str) -> Suggestion:
        return Suggestion("copper", "A", 0.9)


class Advance(BaseModel):
    hours: float


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--data", default="./e2e-data")
    parser.add_argument("--web-origin", default="http://localhost:5174")
    parser.add_argument("--ml-url", default="", help="use a real ML service instead of the stub")
    args = parser.parse_args()

    data = Path(args.data).resolve()
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir(parents=True)

    clock = Clock()
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{(data / 'e2e.db').as_posix()}",
        jwt_secret="e2e-secret-that-is-at-least-32-bytes-long",
        jwt_access_ttl_seconds=3600,
        media_dir=str(data / "media"),
        public_base_url=args.web_origin,
        cors_origins=[args.web_origin],
    )
    classifier = classifier_from_url(args.ml_url) if args.ml_url else FixedClassifier()
    app = create_app(settings, clock=clock, classifier=classifier, gateway=SimulatedGateway())

    Base.metadata.create_all(app.state.engine)
    with app.state.sessionmaker() as db:
        seed_materials(db, clock())
        db.add(
            User(
                phone=ADMIN_PHONE,
                name="Admin",
                password_hash=hash_password(ADMIN_PASSWORD),
                role=Role.ADMIN,
                kyc_status=KycStatus.APPROVED,
                created_at=clock(),
            )
        )
        db.commit()

    @app.post("/__e2e__/advance", include_in_schema=False)
    def advance(body: Advance) -> dict:
        clock.now += timedelta(hours=body.hours)
        return {"now": clock.now.isoformat()}

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
