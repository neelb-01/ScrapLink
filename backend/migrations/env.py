from alembic import context

from scraplink import models  # noqa: F401  (registers every table on Base.metadata)
from scraplink.config import get_settings
from scraplink.db import Base, make_engine

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    # UTCDateTime is a Python-side conversion over a plain DateTime column.
    if type_ == "type" and isinstance(obj, models.UTCDateTime):
        return "sa.DateTime()"
    return False


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        render_item=render_item,
        render_as_batch=True,  # SQLite needs table rebuilds for ALTER; harmless on PostgreSQL
        compare_type=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(url=get_settings().database_url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine(get_settings().database_url)
    with engine.connect() as connection:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
