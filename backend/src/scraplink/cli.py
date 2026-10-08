"""Operator commands: `python -m scraplink.cli <command>`."""

import argparse
import getpass
import json
import sys
from pathlib import Path

from sqlalchemy import select

from .config import get_settings
from .db import Base, make_engine, make_sessionmaker
from .models import KycStatus, Role, User, utcnow
from .security import hash_password
from .seed import seed_materials


def _session():
    return make_sessionmaker(make_engine(get_settings().database_url))()


def cmd_init_db(_: argparse.Namespace) -> None:
    """Create tables directly. Development only — deployed databases use `alembic upgrade head`."""
    Base.metadata.create_all(make_engine(get_settings().database_url))
    print("tables created")


def cmd_seed(_: argparse.Namespace) -> None:
    with _session() as db:
        added = seed_materials(db, utcnow())
        db.commit()
    print(f"{added} materials added")
    if added:
        print("NOTE: seed rates are illustrative. Set real ones: PUT /admin/materials/{code}/rate")


def cmd_create_admin(args: argparse.Namespace) -> None:
    password = args.password or getpass.getpass("Password: ")
    if len(password) < 8:
        sys.exit("password must be at least 8 characters")
    with _session() as db:
        if db.scalars(select(User).where(User.phone == args.phone)).first():
            sys.exit("a user with that phone number already exists")
        db.add(
            User(
                phone=args.phone,
                name=args.name,
                password_hash=hash_password(password),
                role=Role.ADMIN,
                kyc_status=KycStatus.APPROVED,
                created_at=utcnow(),
            )
        )
        db.commit()
    print(f"admin {args.phone} created")


def _run_job(name: str) -> None:
    from .app import create_app
    from .jobs import run_job

    app = create_app()
    run = run_job(app.state.sessionmaker, app.state.env, name)
    print(run.summary)
    if not run.ok:
        sys.exit(1)


def cmd_close_auctions(_: argparse.Namespace) -> None:
    """Close every auction past its deadline, and lapse every award whose buyer didn't pay in
    time. Requests also do both lazily; run this from cron so nothing waits for a visitor."""
    _run_job("close-auctions")


def cmd_anchor_custody(_: argparse.Namespace) -> None:
    """Seal the custody events recorded since the last anchor under one Merkle root."""
    _run_job("anchor-custody")


def cmd_reprice(_: argparse.Namespace) -> None:
    """Move each material's reference price toward what recent paid trades were worth."""
    _run_job("reprice")


def cmd_seed_demo(_: argparse.Namespace) -> None:
    """Load the demo dataset: people, three weeks of trades, requests and agreements."""
    from .demo import DEMO_PASSWORD, PEOPLE, DemoAlreadyLoaded, seed_demo
    from .storage import LocalStorage

    settings = get_settings()
    with _session() as db:
        seed_materials(db, utcnow())
        try:
            summary = seed_demo(db, settings, LocalStorage(settings.media_dir), utcnow())
        except DemoAlreadyLoaded as exc:
            sys.exit(str(exc))
        db.commit()

    print("demo lots: " + ", ".join(f"{n} {s}" for s, n in summary.lots_by_status.items()))
    print(f"\nSign in with any of these (password {DEMO_PASSWORD}):")
    for p in PEOPLE:
        note = "" if p.approved else "  (waiting for approval)"
        print(f"  {p.phone}  {p.role:<6}  {p.name}, {p.business}{note}")


def cmd_export_training(args: argparse.Namespace) -> None:
    """Write lot photos and confirmed materials for `python -m scraplink_ml.train`."""
    from .storage import LocalStorage
    from .training_export import export_training_set

    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} is not empty: choose a new folder so old and new photos don't mix")
    storage = LocalStorage(get_settings().media_dir)
    with _session() as db:
        result = export_training_set(db, storage, out, include_unsettled=args.include_unsettled)
    for code, count in result.per_material.items():
        print(f"  {code:<22} {count}")
    print(f"{result.exported} photos exported to {out}")
    for reason in result.skipped:
        print(f"  skipped {reason}")


def cmd_openapi(args: argparse.Namespace) -> None:
    """Write the API schema; the web client generates its TypeScript types from it."""
    from .app import create_app
    from .config import Settings
    from .payments import SimulatedGateway

    settings = Settings(_env_file=None, database_url="sqlite://", jwt_secret="x" * 32)
    schema = create_app(settings, gateway=SimulatedGateway()).openapi()
    Path(args.out).write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"schema written to {args.out}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="scraplink")
    commands = parser.add_subparsers(required=True)

    commands.add_parser("init-db", help="create tables (development)").set_defaults(
        func=cmd_init_db
    )
    commands.add_parser("seed", help="add the starter catalogue").set_defaults(func=cmd_seed)
    commands.add_parser("close-auctions", help="close due auctions").set_defaults(
        func=cmd_close_auctions
    )
    commands.add_parser("anchor-custody", help="seal new custody events").set_defaults(
        func=cmd_anchor_custody
    )
    commands.add_parser("reprice", help="move reference prices toward recent trades").set_defaults(
        func=cmd_reprice
    )
    commands.add_parser("seed-demo", help="load demo people and trades").set_defaults(
        func=cmd_seed_demo
    )
    export = commands.add_parser("export-training", help="export labelled lot photos for ML")
    export.add_argument("--out", required=True, help="a new, empty folder")
    export.add_argument(
        "--include-unsettled",
        action="store_true",
        help="also export confirmed lots that haven't settled (more photos, noisier labels)",
    )
    export.set_defaults(func=cmd_export_training)
    openapi = commands.add_parser("openapi", help="write the OpenAPI schema to a file")
    openapi.add_argument("--out", required=True)
    openapi.set_defaults(func=cmd_openapi)
    admin = commands.add_parser("create-admin", help="create an admin user")
    admin.add_argument("--phone", required=True)
    admin.add_argument("--name", required=True)
    admin.add_argument("--password", help="prompted for if omitted")
    admin.set_defaults(func=cmd_create_admin)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
