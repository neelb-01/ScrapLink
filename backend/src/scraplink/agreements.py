"""Long-term supply agreements: a fixed monthly quantity at a fixed rate between two parties
who already trade.

First slice: a buyer proposes to a seller they have bought from, and the seller accepts or
declines. Monthly call-offs against an active agreement, deliveries and rate revisions come next.
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import compliance
from .env import Env
from .errors import Conflict, Forbidden, Invalid, NotFound
from .lots import MAX_WEIGHT_GRAMS
from .models import (
    AgreementStatus,
    KycStatus,
    Lot,
    LotStatus,
    Material,
    Role,
    SupplyAgreement,
    User,
)

# The buyer paid for the lot, so the two have actually traded.
_TRADED = (
    LotStatus.FUNDED,
    LotStatus.PICKUP_SCHEDULED,
    LotStatus.DELIVERED,
    LotStatus.SETTLED,
    LotStatus.DISPUTED,
)


def trading_partners(db: Session, buyer: User) -> list[User]:
    """Sellers this buyer has paid for a lot from: the only ones they can propose to."""
    seller_ids = select(Lot.seller_id).where(
        Lot.awarded_buyer_id == buyer.id, Lot.status.in_(_TRADED)
    )
    return list(db.scalars(select(User).where(User.id.in_(seller_ids)).order_by(User.name)))


def propose(
    db: Session,
    env: Env,
    buyer: User,
    *,
    seller_id: uuid.UUID,
    material_code: str,
    monthly_quantity_grams: int,
    rate_paise_per_kg: int,
    starts_on: date,
    months: int,
) -> SupplyAgreement:
    if buyer.role != Role.BUYER:
        raise Forbidden("only buyers can propose supply agreements")
    if buyer.kyc_status != KycStatus.APPROVED:
        raise Forbidden("your KYC is not approved yet")
    if seller_id not in {s.id for s in trading_partners(db, buyer)}:
        raise Forbidden("you can propose an agreement only to a seller you have bought from")
    material = db.scalars(select(Material).where(Material.code == material_code)).first()
    if material is None:
        raise Invalid(f"unknown material '{material_code}'")
    compliance.require_authorised(buyer, material)
    if not 0 < monthly_quantity_grams <= MAX_WEIGHT_GRAMS:
        raise Invalid("monthly quantity must be between 1 g and 100 tonnes")
    if rate_paise_per_kg <= 0:
        raise Invalid("rate must be positive")
    if starts_on <= env.now().date():
        raise Invalid("the agreement must start after today")
    if not 1 <= months <= 24:
        raise Invalid("agreements run between 1 and 24 months")

    agreement = SupplyAgreement(
        buyer_id=buyer.id,
        seller_id=seller_id,
        material_id=material.id,
        material=material,
        monthly_quantity_grams=monthly_quantity_grams,
        rate_paise_per_kg=rate_paise_per_kg,
        starts_on=starts_on,
        months=months,
        status=AgreementStatus.PROPOSED,
        created_at=env.now(),
    )
    db.add(agreement)
    db.flush()
    return agreement


def decide(
    db: Session, env: Env, seller: User, agreement_id: uuid.UUID, *, accept: bool
) -> SupplyAgreement:
    agreement = db.get(SupplyAgreement, agreement_id)
    if agreement is None or seller.id not in (agreement.seller_id, agreement.buyer_id):
        raise NotFound("agreement not found")
    if agreement.seller_id != seller.id:
        raise Forbidden("only the seller can accept or decline this agreement")
    if agreement.status != AgreementStatus.PROPOSED:
        raise Conflict(f"this agreement is already {agreement.status}")
    agreement.status = AgreementStatus.ACTIVE if accept else AgreementStatus.DECLINED
    agreement.decided_at = env.now()
    return agreement


def visible_agreements(db: Session, user: User) -> list[SupplyAgreement]:
    query = select(SupplyAgreement).order_by(SupplyAgreement.created_at.desc())
    if user.role == Role.BUYER:
        query = query.where(SupplyAgreement.buyer_id == user.id)
    elif user.role == Role.SELLER:
        query = query.where(SupplyAgreement.seller_id == user.id)
    return list(db.scalars(query.limit(200)))
