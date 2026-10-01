import uuid
from datetime import datetime
from pathlib import PurePosixPath
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import custody, lots
from ..deps import DB, CurrentUser, EnvDep
from ..env import Env
from ..errors import Conflict, NotFound
from ..models import Bid, Lot, LotStatus, Role, User
from ..schemas import (
    AwardOut,
    BidIn,
    ClassificationOut,
    ConfirmIn,
    CustodyEventOut,
    DisputeIn,
    EscrowOut,
    EstimateOut,
    ListIn,
    LotOut,
    PartyOut,
    PickupIn,
)

router = APIRouter(prefix="/lots", tags=["lots"])

_MEDIA_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _party(user: User) -> PartyOut:
    return PartyOut(id=user.id, name=user.name, business_name=user.business_name)


def _can_view(db: Session, lot: Lot, user: User) -> bool:
    if user.role == Role.ADMIN or lots.is_seller_side(lot, user) or lot.awarded_buyer_id == user.id:
        return True
    if user.role == Role.BUYER:
        if lot.status == LotStatus.LISTED:
            return True
        return (
            db.scalars(select(Bid.id).where(Bid.lot_id == lot.id, Bid.buyer_id == user.id)).first()
            is not None
        )
    return False


def _visible_lot(db: Session, env: Env, lot_id: uuid.UUID, user: User) -> Lot:
    """Load for mutation, applying any auction close that fell due since the last request."""
    lot = lots.load_lot(db, lot_id, for_update=True)
    if not _can_view(db, lot, user):
        # Same answer as a missing lot, so ids cannot be probed.
        raise NotFound("lot not found")
    lots.close_auction_if_due(db, env, lot)
    return lot


def _view(db: Session, env: Env, lot: Lot, user: User) -> LotOut:
    seller_side = user.role == Role.ADMIN or lots.is_seller_side(lot, user)
    bid_count = db.scalar(select(func.count()).select_from(Bid).where(Bid.lot_id == lot.id))
    my_bid = None
    if user.role == Role.BUYER:
        my_bid = db.scalar(
            select(Bid.rate_paise_per_kg).where(Bid.lot_id == lot.id, Bid.buyer_id == user.id)
        )

    award = None
    if lot.awarded_buyer_id and (seller_side or lot.awarded_buyer_id == user.id):
        award = AwardOut(
            buyer=_party(lot.awarded_buyer),
            rate_paise_per_kg=lot.awarded_rate_paise_per_kg,
            escrow_required_paise=lots.escrow_required(env, lot),
        )

    estimate = None
    if lot.estimate_total_paise is not None:
        estimate = EstimateOut(
            reference_rate_paise_per_kg=lot.reference_rate_paise_per_kg,
            rate_paise_per_kg=lot.estimate_rate_paise_per_kg,
            total_paise=lot.estimate_total_paise,
            low_paise=lot.estimate_low_paise,
            high_paise=lot.estimate_high_paise,
        )

    return LotOut(
        id=lot.id,
        status=lot.status,
        created_at=lot.created_at,
        seller=_party(lot.seller),
        captured_by_id=lot.created_by_id,
        photo_url=f"/lots/{lot.id}/photo",
        photo_sha256=lot.photo_sha256,
        classification=ClassificationOut(
            suggested_material_code=lot.suggested_material_code,
            suggested_grade=lot.suggested_grade,
            confidence=lot.suggestion_confidence,
            prefilled=lots.suggestion_is_confident(db, env, lot),
            threshold=env.settings.ml_classification_confidence_threshold,
        ),
        material_code=lot.material.code if lot.material else None,
        material_name=lot.material.name if lot.material else None,
        grade=lot.grade,
        declared_weight_grams=lot.declared_weight_grams,
        estimate=estimate,
        reserve_rate_paise_per_kg=lot.reserve_rate_paise_per_kg if seller_side else None,
        auction_closes_at=lot.auction_closes_at,
        bid_count=bid_count,
        my_bid_rate_paise_per_kg=my_bid,
        award=award,
        pickup_at=lot.pickup_at,
        measured_weight_grams=lot.measured_weight_grams,
        settled_amount_paise=lot.settled_amount_paise,
        certificate_id=lot.certificate.id if lot.certificate else None,
    )


def _file_response(env: Env, key: str) -> Response:
    media_type = _MEDIA_TYPES.get(PurePosixPath(key).suffix, "application/octet-stream")
    return Response(env.storage.get(key), media_type=media_type)


# --- capture ---------------------------------------------------------------------------------


@router.post("", status_code=201, response_model=LotOut)
def create_lot(
    db: DB,
    env: EnvDep,
    user: CurrentUser,
    photo: Annotated[UploadFile, File(description="Photograph of the lot")],
    seller_id: Annotated[
        uuid.UUID | None, Form(description="Required when an agent captures")
    ] = None,
) -> LotOut:
    lot = lots.create_lot(
        db,
        env,
        user,
        photo=photo.file.read(lots.MAX_IMAGE_BYTES + 1),
        content_type=photo.content_type,
        seller_id=seller_id,
    )
    db.commit()
    return _view(db, env, lot, user)


@router.get("", response_model=list[LotOut])
def list_lots(
    db: DB, env: EnvDep, user: CurrentUser, scope: Literal["mine", "market"] = "mine"
) -> list[LotOut]:
    query = select(Lot)
    if scope == "market":
        query = query.where(Lot.status == LotStatus.LISTED, Lot.auction_closes_at > env.now())
        query = query.order_by(Lot.auction_closes_at)
    else:
        if user.role == Role.BUYER:
            bid_on = select(Bid.lot_id).where(Bid.buyer_id == user.id)
            query = query.where(or_(Lot.awarded_buyer_id == user.id, Lot.id.in_(bid_on)))
        elif user.role != Role.ADMIN:
            query = query.where(or_(Lot.seller_id == user.id, Lot.created_by_id == user.id))
        query = query.order_by(Lot.created_at.desc())
    found = list(db.scalars(query.limit(200)))
    for lot in found:
        lots.close_auction_if_due(db, env, lot)
    db.commit()
    return [_view(db, env, lot, user) for lot in found]


@router.get("/{lot_id}", response_model=LotOut)
def get_lot(lot_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> LotOut:
    lot = _visible_lot(db, env, lot_id, user)
    db.commit()
    return _view(db, env, lot, user)


@router.get("/{lot_id}/photo")
def lot_photo(lot_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> Response:
    lot = _visible_lot(db, env, lot_id, user)
    db.commit()
    return _file_response(env, lot.photo_key)


@router.post("/{lot_id}/confirm", response_model=LotOut)
def confirm_lot(
    lot_id: uuid.UUID, body: ConfirmIn, db: DB, env: EnvDep, user: CurrentUser
) -> LotOut:
    lot = _visible_lot(db, env, lot_id, user)
    lots.confirm_lot(
        db,
        env,
        user,
        lot,
        material_code=body.material_code,
        grade=body.grade,
        declared_weight_grams=body.declared_weight_grams,
    )
    db.commit()
    return _view(db, env, lot, user)


# --- auction ---------------------------------------------------------------------------------


@router.post("/{lot_id}/list", response_model=LotOut)
def list_lot(lot_id: uuid.UUID, body: ListIn, db: DB, env: EnvDep, user: CurrentUser) -> LotOut:
    lot = _visible_lot(db, env, lot_id, user)
    lots.list_lot(
        db,
        env,
        user,
        lot,
        auction_hours=body.auction_hours,
        reserve_rate_paise_per_kg=body.reserve_rate_paise_per_kg,
    )
    db.commit()
    return _view(db, env, lot, user)


@router.post("/{lot_id}/bids", response_model=LotOut)
def place_bid(lot_id: uuid.UUID, body: BidIn, db: DB, env: EnvDep, user: CurrentUser) -> LotOut:
    lot = _visible_lot(db, env, lot_id, user)
    if lot.status != LotStatus.LISTED:
        db.commit()  # keep the close that _visible_lot may just have applied
        raise Conflict("bidding on this lot has closed")
    lots.place_bid(db, env, user, lot, rate_paise_per_kg=body.rate_paise_per_kg)
    db.commit()
    return _view(db, env, lot, user)


class BidOut(BaseModel):
    buyer: PartyOut
    rate_paise_per_kg: int
    placed_at: datetime


@router.get("/{lot_id}/bids", response_model=list[BidOut])
def bids(lot_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> list[BidOut]:
    """Sealed until close: before then a buyer sees only their own bid and the seller none."""
    lot = _visible_lot(db, env, lot_id, user)
    db.commit()
    query = select(Bid).where(Bid.lot_id == lot.id)
    seller_side = user.role == Role.ADMIN or lots.is_seller_side(lot, user)
    if lot.status == LotStatus.LISTED or not seller_side:
        if user.role != Role.BUYER:
            return []
        query = query.where(Bid.buyer_id == user.id)
    ranked = db.scalars(query.order_by(Bid.rate_paise_per_kg.desc(), Bid.placed_at, Bid.id))
    return [
        BidOut(
            buyer=_party(db.get(User, b.buyer_id)),
            rate_paise_per_kg=b.rate_paise_per_kg,
            placed_at=b.placed_at,
        )
        for b in ranked
    ]


# --- escrow, fulfilment, settlement ----------------------------------------------------------


@router.post("/{lot_id}/escrow", response_model=EscrowOut)
def start_escrow(lot_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> EscrowOut:
    lot = _visible_lot(db, env, lot_id, user)
    intent = lots.start_escrow(db, env, user, lot)
    db.commit()
    return EscrowOut(
        intent_id=intent.id,
        gateway=intent.gateway,
        gateway_order_id=intent.gateway_order_id,
        amount_paise=intent.amount_paise,
        status=intent.status,
        razorpay_key_id=getattr(env.gateway, "key_id", None)
        if intent.gateway == "razorpay"
        else None,
    )


@router.post("/{lot_id}/pickup", response_model=LotOut)
def schedule_pickup(
    lot_id: uuid.UUID, body: PickupIn, db: DB, env: EnvDep, user: CurrentUser
) -> LotOut:
    lot = _visible_lot(db, env, lot_id, user)
    lots.schedule_pickup(db, env, user, lot, pickup_at=body.pickup_at)
    db.commit()
    return _view(db, env, lot, user)


@router.post("/{lot_id}/delivery", response_model=LotOut)
def record_delivery(
    lot_id: uuid.UUID,
    db: DB,
    env: EnvDep,
    user: CurrentUser,
    measured_weight_grams: Annotated[int, Form(gt=0, le=100_000_000)],
    slip: Annotated[UploadFile, File(description="Photograph of the weighbridge slip")],
) -> LotOut:
    lot = _visible_lot(db, env, lot_id, user)
    lots.record_delivery(
        db,
        env,
        user,
        lot,
        measured_weight_grams=measured_weight_grams,
        slip=slip.file.read(lots.MAX_IMAGE_BYTES + 1),
        slip_content_type=slip.content_type,
    )
    db.commit()
    return _view(db, env, lot, user)


@router.get("/{lot_id}/weighbridge-slip")
def weighbridge_slip(lot_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> Response:
    lot = _visible_lot(db, env, lot_id, user)
    db.commit()
    if lot.weighbridge_slip_key is None:
        raise NotFound("no weighbridge slip recorded yet")
    return _file_response(env, lot.weighbridge_slip_key)


@router.post("/{lot_id}/delivery/accept", response_model=LotOut)
def accept_delivery(lot_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> LotOut:
    lot = _visible_lot(db, env, lot_id, user)
    lots.accept_delivery(db, env, user, lot)
    db.commit()
    return _view(db, env, lot, user)


@router.post("/{lot_id}/delivery/dispute", response_model=LotOut)
def dispute_delivery(
    lot_id: uuid.UUID, body: DisputeIn, db: DB, env: EnvDep, user: CurrentUser
) -> LotOut:
    lot = _visible_lot(db, env, lot_id, user)
    lots.dispute_delivery(db, env, user, lot, reason=body.reason)
    db.commit()
    return _view(db, env, lot, user)


@router.get("/{lot_id}/custody", response_model=list[CustodyEventOut])
def custody_record(lot_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser):
    """Parties to the trade only: the record carries the seller's reserve and the award."""
    lot = _visible_lot(db, env, lot_id, user)
    db.commit()
    is_party = (
        user.role == Role.ADMIN or lots.is_seller_side(lot, user) or lot.awarded_buyer_id == user.id
    )
    if not is_party:
        raise NotFound("lot not found")
    return custody.lot_events(db, lot.id)
