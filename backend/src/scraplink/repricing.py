"""Dynamic pricing: each material's reference price follows what recent trades actually paid.

Run nightly by the `reprice` job (jobs.py). For every material it takes the paid trades of the
last `reprice_window_days`, converts each winning price to grade A, and moves the reference
price part of the way toward their median (pricing.market_move). Every move is a new
ReferenceRate row that records the trades behind it, so the old price is never lost and the
seller can be told why the price changed.

Guard rails, all in settings:
- too few trades in the window, and the price holds;
- each run moves the price by at most a fixed share of it;
- moves too small to matter are skipped, so the history isn't filled with noise;
- a price an admin sets is a reset: only trades whose auctions closed after it count.

A trade counts once its buyer has paid into escrow: a winning bid that is never paid says
little about what the material is worth. Cancelled trades don't count.
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import pricing
from .env import Env
from .lots import current_rate
from .models import Lot, LotStatus, Material, RateSource, ReferenceRate

PAID_STATUSES = (
    LotStatus.FUNDED,
    LotStatus.PICKUP_SCHEDULED,
    LotStatus.DELIVERED,
    LotStatus.DISPUTED,
    LotStatus.SETTLED,
)


@dataclass(frozen=True)
class Outcome:
    material: Material
    # The new rate, or None when the price held.
    moved_to: ReferenceRate | None
    # Why it held, in a few words; empty when it moved.
    held_because: str = ""


def recent_trade_rates(db: Session, env: Env, material: Material, since) -> list[int]:
    """Grade A equivalents of the paid trades whose auctions closed after `since`."""
    rows = db.execute(
        select(Lot.awarded_rate_paise_per_kg, Lot.grade).where(
            Lot.material_id == material.id,
            Lot.status.in_(PAID_STATUSES),
            Lot.awarded_rate_paise_per_kg.is_not(None),
            Lot.auction_closes_at > since,
            Lot.auction_closes_at <= env.now(),
        )
    )
    return [pricing.grade_a_equivalent(rate, grade) for rate, grade in rows]


def _evidence_since(db: Session, env: Env, material: Material):
    window_start = env.now() - timedelta(days=env.settings.reprice_window_days)
    last_admin = db.scalars(
        select(ReferenceRate.effective_from)
        .where(
            ReferenceRate.material_id == material.id,
            ReferenceRate.source == RateSource.ADMIN,
            ReferenceRate.effective_from <= env.now(),
        )
        .order_by(ReferenceRate.effective_from.desc())
        .limit(1)
    ).first()
    return max(window_start, last_admin) if last_admin else window_start


def reprice_material(db: Session, env: Env, material: Material) -> Outcome:
    settings = env.settings
    current = current_rate(db, material, env.now())
    if current is None:
        return Outcome(material, None, "no price set")
    rates = recent_trade_rates(db, env, material, _evidence_since(db, env, material))
    if len(rates) < settings.reprice_min_trades:
        return Outcome(
            material, None, f"{len(rates)} of {settings.reprice_min_trades} trades needed"
        )
    move = pricing.market_move(
        current.rate_paise_per_kg,
        rates,
        blend=settings.reprice_blend,
        max_step=settings.reprice_max_step,
    )
    change = abs(move.rate_paise_per_kg - current.rate_paise_per_kg)
    if change == 0 or change < current.rate_paise_per_kg * settings.reprice_min_move:
        return Outcome(material, None, "trades match the price")
    rate = ReferenceRate(
        material_id=material.id,
        rate_paise_per_kg=move.rate_paise_per_kg,
        effective_from=env.now(),
        source=RateSource.MARKET,
        previous_rate_paise_per_kg=current.rate_paise_per_kg,
        trade_count=len(rates),
        window_days=settings.reprice_window_days,
        market_median_paise_per_kg=move.median_paise_per_kg,
        capped=move.capped,
    )
    db.add(rate)
    db.flush()
    return Outcome(material, rate)


def reprice_all(db: Session, env: Env) -> list[Outcome]:
    """Caller commits."""
    materials = db.scalars(select(Material).order_by(Material.id))
    return [reprice_material(db, env, material) for material in materials]


def _rupees(paise: int) -> str:
    return f"₹{paise // 100:,}" + (f".{paise % 100:02d}" if paise % 100 else "")


def summarise(outcomes: list[Outcome]) -> str:
    moved = [(o.material, o.moved_to) for o in outcomes if o.moved_to is not None]
    parts = [
        f"{material.name} {_rupees(rate.previous_rate_paise_per_kg)}"
        f"→{_rupees(rate.rate_paise_per_kg)} on {rate.trade_count} trades"
        for material, rate in moved
    ]
    held = len(outcomes) - len(moved)
    if not parts:
        return f"no prices moved ({held} held)"
    return "; ".join(parts) + f"; {held} held"
