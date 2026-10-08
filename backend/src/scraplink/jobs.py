"""Scheduled jobs, and a record of every run.

The same functions run from the arq worker (worker.py), from cron through the CLI, or when an
admin presses "Run now", and each run is logged in job_runs either way.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from . import anchoring, repricing
from .env import Env
from .lots import close_auction_if_due, lapse_award_if_due, load_lot
from .models import JobRun, Lot, LotStatus

log = logging.getLogger(__name__)


def close_due_auctions(sessions: sessionmaker[Session], env: Env) -> str:
    """Close every auction past its deadline, and lapse every award whose buyer didn't pay in
    time. Requests also do both lazily; the schedule makes sure nothing waits for a visitor."""
    with sessions() as db:
        due = db.scalars(
            select(Lot.id).where(Lot.status == LotStatus.LISTED, Lot.auction_closes_at <= env.now())
        )
        closed = 0
        for lot_id in list(due):
            closed += close_auction_if_due(db, env, load_lot(db, lot_id, for_update=True))
            db.commit()
        unpaid = db.scalars(
            select(Lot.id).where(Lot.status == LotStatus.AWARDED, Lot.escrow_due_at <= env.now())
        )
        lapsed = 0
        for lot_id in list(unpaid):
            lapsed += lapse_award_if_due(db, env, load_lot(db, lot_id, for_update=True))
            db.commit()
    return f"{closed} auctions closed, {lapsed} unpaid awards passed on"


def anchor_custody(sessions: sessionmaker[Session], env: Env) -> str:
    with sessions() as db:
        anchor = anchoring.anchor_new_events(db, env)
        db.commit()
        if anchor is None:
            return "no new custody events to seal"
        return f"sealed {anchor.event_count} events under root {anchor.merkle_root[:12]}…"


def reprice(sessions: sessionmaker[Session], env: Env) -> str:
    with sessions() as db:
        outcomes = repricing.reprice_all(db, env)
        db.commit()
        return repricing.summarise(outcomes)


@dataclass(frozen=True)
class Job:
    name: str
    schedule: str
    description: str
    run: Callable[[sessionmaker[Session], Env], str]


JOBS: dict[str, Job] = {
    job.name: job
    for job in (
        Job(
            "close-auctions",
            "Every minute",
            "Closes auctions that have ended and passes unpaid wins to the next bidder.",
            close_due_auctions,
        ),
        Job(
            "anchor-custody",
            "Daily at 00:05",
            "Seals the day's custody events under one Merkle root.",
            anchor_custody,
        ),
        Job(
            "reprice",
            "Daily at 00:15",
            "Moves each material's reference price toward what recent paid trades were worth.",
            reprice,
        ),
    )
}


def run_job(sessions: sessionmaker[Session], env: Env, name: str) -> JobRun:
    """Run a job now and record the outcome. A failure is recorded, not raised."""
    job = JOBS[name]
    started = env.now()
    try:
        summary, ok = job.run(sessions, env)[:500], True
    except Exception as exc:
        log.exception("job %s failed", name)
        summary, ok = f"failed: {exc}"[:500], False
    with sessions() as db:
        run = JobRun(name=name, started_at=started, finished_at=env.now(), ok=ok, summary=summary)
        db.add(run)
        db.commit()
        db.refresh(run)
        db.expunge(run)
    return run


def last_runs(db: Session) -> dict[str, JobRun]:
    runs: dict[str, JobRun] = {}
    for name in JOBS:
        run = db.scalars(
            select(JobRun).where(JobRun.name == name).order_by(JobRun.id.desc()).limit(1)
        ).first()
        if run is not None:
            runs[name] = run
    return runs
