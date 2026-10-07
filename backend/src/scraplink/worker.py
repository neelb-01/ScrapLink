"""Background worker: runs the scheduled jobs off the request path.

    pip install -e ".[worker]"
    arq scraplink.worker.WorkerSettings        # needs Redis at REDIS_URL

First slice: the two scheduled jobs, run on arq's cron. Queued work from requests (route
optimisation, payment webhook reconciliation) moves here as those modules grow. Until a worker
is deployed, `python -m scraplink.cli close-auctions` and `anchor-custody` from cron do the same.
"""

import asyncio

from arq import cron
from arq.connections import RedisSettings

from .app import create_app
from .config import get_settings
from .jobs import run_job


async def startup(ctx: dict) -> None:
    ctx["app"] = create_app()


async def shutdown(ctx: dict) -> None:
    ctx["app"].state.engine.dispose()


def _job(name: str):
    async def run(ctx: dict) -> str:
        state = ctx["app"].state
        # The jobs use the synchronous database session, so keep them off the event loop.
        result = await asyncio.to_thread(run_job, state.sessionmaker, state.env, name)
        return result.summary

    run.__name__ = name.replace("-", "_")
    return run


class WorkerSettings:
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    cron_jobs = [
        cron(_job("close-auctions"), name="close-auctions"),  # second=0 of every minute
        cron(_job("anchor-custody"), name="anchor-custody", hour={0}, minute={5}),
    ]
