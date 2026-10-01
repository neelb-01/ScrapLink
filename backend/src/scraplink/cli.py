"""Operator commands: `python -m scraplink.cli <command>`."""

import argparse
import getpass
import json
import sys
from pathlib import Path

from sqlalchemy import select

from .config import get_settings
from .db import Base, make_engine, make_sessionmaker
from .models import KycStatus, Lot, LotStatus, Role, User, utcnow
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


def cmd_close_auctions(_: argparse.Namespace) -> None:
    """Close every auction past its deadline. Requests also close lazily; run this from cron."""
    from .app import create_app
    from .lots import close_auction_if_due

    app = create_app()
    env = app.state.env
    with app.state.sessionmaker() as db:
        due = db.scalars(
            select(Lot).where(Lot.status == LotStatus.LISTED, Lot.auction_closes_at <= env.now())
        )
        closed = sum(close_auction_if_due(db, env, lot) for lot in list(due))
        db.commit()
    print(f"{closed} auctions closed")


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
    commands.add_parser("seed", help="add the metal-scrap catalogue").set_defaults(func=cmd_seed)
    commands.add_parser("close-auctions", help="close due auctions").set_defaults(
        func=cmd_close_auctions
    )
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
