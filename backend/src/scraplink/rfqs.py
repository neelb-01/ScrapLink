"""Requests for quotation: a buyer states what they want and sellers see the demand.

First slice: buyers post and close requests, and sellers see the open ones. Sellers can't
quote against a request yet; that, and turning an accepted quote into a lot, comes next.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import compliance
from .env import Env
from .errors import Conflict, Forbidden, Invalid
from .lots import MAX_WEIGHT_GRAMS
from .models import KycStatus, Material, Rfq, RfqStatus, Role, User


def create_rfq(
    db: Session,
    env: Env,
    buyer: User,
    *,
    material_code: str,
    quantity_grams: int,
    target_rate_paise_per_kg: int | None,
    needed_by: datetime,
    note: str,
) -> Rfq:
    if buyer.role != Role.BUYER:
        raise Forbidden("only buyers can post requests")
    if buyer.kyc_status != KycStatus.APPROVED:
        raise Forbidden("your KYC is not approved yet")
    material = db.scalars(select(Material).where(Material.code == material_code)).first()
    if material is None:
        raise Invalid(f"unknown material '{material_code}'")
    compliance.require_authorised(buyer, material)
    if not 0 < quantity_grams <= MAX_WEIGHT_GRAMS:
        raise Invalid("quantity must be between 1 g and 100 tonnes")
    if needed_by <= env.now():
        raise Invalid("the needed-by date must be in the future")

    rfq = Rfq(
        buyer_id=buyer.id,
        material_id=material.id,
        material=material,
        quantity_grams=quantity_grams,
        target_rate_paise_per_kg=target_rate_paise_per_kg,
        needed_by=needed_by,
        note=note.strip(),
        status=RfqStatus.OPEN,
        created_at=env.now(),
    )
    db.add(rfq)
    db.flush()
    return rfq


def close_rfq(buyer: User, rfq: Rfq) -> Rfq:
    if rfq.buyer_id != buyer.id:
        raise Forbidden("only the buyer who posted this request can close it")
    if rfq.status != RfqStatus.OPEN:
        raise Conflict("this request is already closed")
    rfq.status = RfqStatus.CLOSED
    return rfq


def visible_rfqs(db: Session, env: Env, user: User) -> list[Rfq]:
    """Buyers see their own requests; sellers see every open one that is still current."""
    query = select(Rfq)
    if user.role == Role.BUYER:
        query = query.where(Rfq.buyer_id == user.id).order_by(Rfq.created_at.desc())
    elif user.role == Role.SELLER:
        query = query.where(Rfq.status == RfqStatus.OPEN, Rfq.needed_by > env.now())
        query = query.order_by(Rfq.needed_by)
    else:
        query = query.order_by(Rfq.created_at.desc())
    return list(db.scalars(query.limit(200)))
