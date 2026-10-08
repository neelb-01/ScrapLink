"""Admin operations: transporters, pickup routes, custody anchors and scheduled jobs."""

from datetime import date

import httpx
from fastapi import APIRouter, Request
from sqlalchemy import func, select

from .. import anchoring, jobs, ledger, lots, routing
from ..deps import DB, Admin, EnvDep
from ..errors import Conflict, NotFound
from ..models import (
    CustodyAnchor,
    LedgerAccount,
    LedgerPosting,
    Lot,
    LotStatus,
    Notification,
    Transporter,
    User,
)
from ..schemas import (
    AnchorCheckOut,
    AnchorOut,
    CountOut,
    DisputeInfoOut,
    DisputeOut,
    JobOut,
    JobRunOut,
    LocationOut,
    MlStatusOut,
    OverviewOut,
    PartyOut,
    RouteOut,
    RouteStopOut,
    TransporterIn,
    TransporterOut,
)

router = APIRouter(prefix="/admin", tags=["operations"])


# --- disputes --------------------------------------------------------------------------------


def _party(user: User) -> PartyOut:
    return PartyOut(id=user.id, name=user.name, business_name=user.business_name)


@router.get("/disputes", response_model=list[DisputeOut])
def disputes(db: DB, _: Admin) -> list[DisputeOut]:
    """Every trade on hold, oldest first: the money waits in escrow until an admin resolves it."""
    found = []
    for lot in db.scalars(
        select(Lot).where(Lot.status == LotStatus.DISPUTED).order_by(Lot.created_at)
    ):
        details = lots.dispute_details(db, lot)
        held = ledger.balance(db, ledger.escrow_account(db, lot.id))
        found.append(
            DisputeOut(
                lot_id=lot.id,
                material_name=lot.material.name,
                seller=_party(lot.seller),
                buyer=_party(db.get(User, lot.awarded_buyer_id)),
                dispute=DisputeInfoOut(
                    raised_by=details.raised_by,
                    reason=details.reason,
                    raised_at=details.raised_at,
                ),
                rate_paise_per_kg=lot.awarded_rate_paise_per_kg,
                declared_weight_grams=lot.declared_weight_grams,
                measured_weight_grams=lot.measured_weight_grams,
                escrow_held_paise=held,
                max_settle_weight_grams=lots.max_settle_weight_grams(lot, held),
            )
        )
    return found


# --- transporters ----------------------------------------------------------------------------


@router.get("/transporters", response_model=list[TransporterOut])
def transporters(db: DB, _: Admin) -> list[Transporter]:
    return list(db.scalars(select(Transporter).order_by(Transporter.name)))


@router.post("/transporters", status_code=201, response_model=TransporterOut)
def add_transporter(body: TransporterIn, db: DB, env: EnvDep, _: Admin) -> Transporter:
    transporter = Transporter(**body.model_dump(), created_at=env.now())
    db.add(transporter)
    db.commit()
    return transporter


# --- routes ----------------------------------------------------------------------------------


def _stop(lot: Lot, leg_metres: int | None) -> RouteStopOut:
    return RouteStopOut(
        lot_id=lot.id,
        seller=PartyOut(
            id=lot.seller.id, name=lot.seller.name, business_name=lot.seller.business_name
        ),
        material_name=lot.material.name if lot.material else None,
        pickup_at=lot.pickup_at,
        location=None
        if lot.pickup_latitude is None
        else LocationOut(latitude=lot.pickup_latitude, longitude=lot.pickup_longitude),
        transporter_name=lot.transporter.name if lot.transporter else None,
        leg_metres=leg_metres,
    )


@router.get("/routes", response_model=RouteOut)
def route(day: date, db: DB, env: EnvDep, _: Admin) -> RouteOut:
    """The day's booked pickups in a suggested visiting order (Indian calendar day)."""
    depot = (env.settings.depot_latitude, env.settings.depot_longitude)
    plan = routing.plan_day(db, day, depot)
    return RouteOut(
        day=plan.day,
        depot=LocationOut(latitude=depot[0], longitude=depot[1]),
        stops=[_stop(s.lot, s.leg_metres) for s in plan.stops],
        unplaced=[_stop(lot, None) for lot in plan.unplaced],
        return_metres=plan.return_metres,
        total_metres=plan.total_metres,
    )


# --- custody anchors -------------------------------------------------------------------------


@router.get("/anchors", response_model=list[AnchorOut])
def anchors(db: DB, _: Admin) -> list[CustodyAnchor]:
    return list(db.scalars(select(CustodyAnchor).order_by(CustodyAnchor.id.desc()).limit(100)))


@router.post("/anchors", status_code=201, response_model=AnchorOut)
def seal(db: DB, env: EnvDep, _: Admin) -> CustodyAnchor:
    anchor = anchoring.anchor_new_events(db, env)
    if anchor is None:
        raise Conflict("no custody events have been recorded since the last anchor")
    db.commit()
    return anchor


@router.get("/anchors/{anchor_id}/check", response_model=AnchorCheckOut)
def check(anchor_id: int, db: DB, _: Admin) -> AnchorCheckOut:
    anchor = db.get(CustodyAnchor, anchor_id)
    if anchor is None:
        raise NotFound("anchor not found")
    return AnchorCheckOut(id=anchor.id, holds=anchoring.anchor_holds(db, anchor))


# --- scheduled jobs --------------------------------------------------------------------------


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: DB, _: Admin) -> list[JobOut]:
    last = jobs.last_runs(db)
    return [
        JobOut(
            name=job.name,
            schedule=job.schedule,
            description=job.description,
            last_run=JobRunOut.model_validate(last[job.name]) if job.name in last else None,
        )
        for job in jobs.JOBS.values()
    ]


@router.post("/jobs/{name}/run", response_model=JobRunOut)
def run_now(name: str, request: Request, env: EnvDep, _: Admin) -> JobRunOut:
    if name not in jobs.JOBS:
        raise NotFound("no such job")
    return JobRunOut.model_validate(jobs.run_job(request.app.state.sessionmaker, env, name))


# --- platform overview -----------------------------------------------------------------------


def _ml_status(url: str) -> MlStatusOut:
    if not url:
        return MlStatusOut(configured=False, reachable=False, model=None)
    try:
        response = httpx.get(url.rstrip("/") + "/health", timeout=1.5)
        response.raise_for_status()
        return MlStatusOut(configured=True, reachable=True, model=response.json().get("model"))
    except (httpx.HTTPError, ValueError):
        return MlStatusOut(configured=True, reachable=False, model=None)


@router.get("/overview", response_model=OverviewOut)
def overview(db: DB, env: EnvDep, _: Admin) -> OverviewOut:
    """Platform monitoring at a glance: people, lots, money, notifications, jobs, ML."""
    users = db.execute(
        select(User.role, User.kyc_status, func.count()).group_by(User.role, User.kyc_status)
    ).all()
    people = [
        CountOut(name=f"{role} ({status})", count=count)
        for role, status, count in sorted(users)
        if role != "admin"
    ]
    lot_counts = db.execute(select(Lot.status, func.count()).group_by(Lot.status)).all()
    escrow = db.scalar(
        select(func.coalesce(func.sum(LedgerPosting.amount_paise), 0))
        .join(LedgerAccount, LedgerAccount.id == LedgerPosting.account_id)
        .where(LedgerAccount.kind == "escrow")
    )
    traded = db.scalar(
        select(func.coalesce(func.sum(Lot.settled_amount_paise), 0)).where(
            Lot.status == LotStatus.SETTLED
        )
    )
    sent = db.scalar(select(func.count()).select_from(Notification))
    emailed = db.scalar(
        select(func.count()).select_from(Notification).where(Notification.emailed_at.is_not(None))
    )
    return OverviewOut(
        users=people,
        lots=[CountOut(name=status, count=count) for status, count in sorted(lot_counts)],
        escrow_held_paise=int(escrow),
        traded_paise=int(traded),
        notifications_sent=sent,
        emails_sent=emailed,
        jobs=list_jobs(db, _),
        ml=_ml_status(env.settings.ml_service_url),
    )
