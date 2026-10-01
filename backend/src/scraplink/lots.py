"""Lot lifecycle — the single trade path of the first slice.

    DRAFT --confirm--> DRAFT --list--> LISTED --close--> AWARDED | UNSOLD
    AWARDED --escrow captured--> FUNDED --pickup--> PICKUP_SCHEDULED
    PICKUP_SCHEDULED --weighbridge--> DELIVERED --seller accepts--> SETTLED (+ certificate)
                                               --seller disputes, or payable > escrow--> DISPUTED

Every transition appends a custody event in the same database transaction as the state
change, so the chain and the lot can never disagree.
"""

import hashlib
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import custody, ledger, pricing
from .certificates import issue_certificate
from .env import Env
from .errors import Conflict, Forbidden, Invalid, NotFound
from .models import (
    Bid,
    KycStatus,
    Lot,
    LotStatus,
    Material,
    PaymentIntent,
    PaymentStatus,
    ReferenceRate,
    Role,
    User,
)

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_WEIGHT_GRAMS = 100_000_000  # 100 tonnes


# --- helpers ---------------------------------------------------------------------------------


def _record(db: Session, env: Env, lot: Lot, event_type: str, payload: dict, actor: User | None):
    custody.append_event(db, lot, event_type, payload, actor=actor, now=env.now())


def _require_approved(user: User, whose: str) -> None:
    if user.kyc_status != KycStatus.APPROVED:
        raise Forbidden(f"{whose} KYC is not approved yet")


def _require_status(lot: Lot, *allowed: LotStatus) -> None:
    if lot.status not in allowed:
        wanted = " or ".join(allowed)
        raise Conflict(f"lot is {lot.status}; this action needs it to be {wanted}")


def is_seller_side(lot: Lot, user: User) -> bool:
    return user.id == lot.seller_id


def _require_seller_side(lot: Lot, user: User) -> None:
    if not is_seller_side(lot, user):
        raise Forbidden("only the seller of this lot can do this")


def _require_awarded_buyer(lot: Lot, user: User) -> None:
    if lot.awarded_buyer_id != user.id:
        raise Forbidden("only the winning buyer can do this")


def _check_image(data: bytes, content_type: str | None) -> str:
    extension = IMAGE_TYPES.get(content_type or "")
    if extension is None:
        raise Invalid("upload a JPEG, PNG or WebP image")
    if not data:
        raise Invalid("the uploaded image is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise Invalid("images must be 10 MB or smaller")
    return extension


def load_lot(db: Session, lot_id: uuid.UUID, *, for_update: bool = False) -> Lot:
    query = select(Lot).where(Lot.id == lot_id)
    if for_update:
        query = query.with_for_update()
    lot = db.scalars(query).first()
    if lot is None:
        raise NotFound("lot not found")
    return lot


def current_rate(db: Session, material: Material, now: datetime) -> ReferenceRate | None:
    return db.scalars(
        select(ReferenceRate)
        .where(ReferenceRate.material_id == material.id, ReferenceRate.effective_from <= now)
        .order_by(ReferenceRate.effective_from.desc(), ReferenceRate.id.desc())
        .limit(1)
    ).first()


def suggestion_is_confident(db: Session, env: Env, lot: Lot) -> bool:
    if lot.suggested_material_code is None or lot.suggestion_confidence is None:
        return False
    if lot.suggestion_confidence < env.settings.ml_classification_confidence_threshold:
        return False
    known = db.scalars(select(Material).where(Material.code == lot.suggested_material_code)).first()
    return known is not None


# --- capture and valuation -------------------------------------------------------------------


def create_lot(
    db: Session,
    env: Env,
    actor: User,
    *,
    photo: bytes,
    content_type: str | None,
) -> Lot:
    if actor.role != Role.SELLER:
        raise Forbidden("only sellers can create lots")
    _require_approved(actor, "your")

    extension = _check_image(photo, content_type)
    digest = hashlib.sha256(photo).hexdigest()
    suggestion = env.classifier.classify(photo, content_type)

    lot = Lot(
        seller_id=actor.id,
        created_by_id=actor.id,
        status=LotStatus.DRAFT,
        created_at=env.now(),
        photo_key=env.storage.put("lots", photo, extension),
        photo_sha256=digest,
    )
    if suggestion is not None:
        lot.suggested_material_code = suggestion.material_code
        lot.suggested_grade = suggestion.grade
        lot.suggestion_confidence = suggestion.confidence
    db.add(lot)
    db.flush()

    _record(
        db,
        env,
        lot,
        "lot.created",
        {
            "seller_id": str(actor.id),
            "photo_sha256": digest,
            "suggestion": None
            if suggestion is None
            else {
                "material_code": suggestion.material_code,
                "grade": suggestion.grade,
                "confidence": f"{suggestion.confidence:.4f}",
            },
        },
        actor,
    )
    return lot


def confirm_lot(
    db: Session,
    env: Env,
    actor: User,
    lot: Lot,
    *,
    material_code: str,
    grade: str,
    declared_weight_grams: int,
) -> Lot:
    """The human verification step: the seller states what the lot is."""
    _require_seller_side(lot, actor)
    _require_status(lot, LotStatus.DRAFT)
    if grade not in pricing.GRADES:
        raise Invalid("grade must be A, B or C")
    if not 0 < declared_weight_grams <= MAX_WEIGHT_GRAMS:
        raise Invalid("declared weight must be between 1 g and 100 tonnes")
    material = db.scalars(select(Material).where(Material.code == material_code)).first()
    if material is None:
        raise Invalid(f"unknown material '{material_code}'")
    rate = current_rate(db, material, env.now())
    if rate is None:
        raise Conflict(f"no reference rate is set for {material.name} yet")

    estimate = pricing.estimate(
        rate.rate_paise_per_kg, grade, declared_weight_grams, env.settings.price_band
    )
    lot.material_id = material.id
    lot.material = material
    lot.grade = grade
    lot.declared_weight_grams = declared_weight_grams
    lot.reference_rate_paise_per_kg = rate.rate_paise_per_kg
    lot.estimate_rate_paise_per_kg = estimate.rate_paise_per_kg
    lot.estimate_total_paise = estimate.total_paise
    lot.estimate_low_paise = estimate.low_paise
    lot.estimate_high_paise = estimate.high_paise

    _record(
        db,
        env,
        lot,
        "lot.confirmed",
        {
            "material_code": material.code,
            "grade": grade,
            "declared_weight_grams": declared_weight_grams,
            "suggestion_accepted": material.code == lot.suggested_material_code
            and grade == lot.suggested_grade,
            "reference_rate_paise_per_kg": rate.rate_paise_per_kg,
            "estimate_total_paise": estimate.total_paise,
        },
        actor,
    )
    return lot


# --- auction ---------------------------------------------------------------------------------


def list_lot(
    db: Session,
    env: Env,
    actor: User,
    lot: Lot,
    *,
    auction_hours: int,
    reserve_rate_paise_per_kg: int | None,
) -> Lot:
    _require_seller_side(lot, actor)
    _require_status(lot, LotStatus.DRAFT)
    if lot.material_id is None:
        raise Conflict("confirm the material, grade and weight before listing")
    if not 1 <= auction_hours <= 168:
        raise Invalid("auctions run between 1 hour and 7 days")

    lot.status = LotStatus.LISTED
    lot.auction_closes_at = env.now() + timedelta(hours=auction_hours)
    lot.reserve_rate_paise_per_kg = reserve_rate_paise_per_kg
    _record(
        db,
        env,
        lot,
        "lot.listed",
        {
            "auction_closes_at": lot.auction_closes_at.isoformat(),
            "reserve_rate_paise_per_kg": reserve_rate_paise_per_kg,
        },
        actor,
    )
    return lot


def place_bid(db: Session, env: Env, buyer: User, lot: Lot, *, rate_paise_per_kg: int) -> Bid:
    if buyer.role != Role.BUYER:
        raise Forbidden("only buyers can bid")
    _require_approved(buyer, "your")
    _require_status(lot, LotStatus.LISTED)
    if env.now() >= lot.auction_closes_at:
        raise Conflict("bidding on this lot has closed")
    if rate_paise_per_kg <= 0:
        raise Invalid("bid rate must be positive")

    bid = db.scalars(select(Bid).where(Bid.lot_id == lot.id, Bid.buyer_id == buyer.id)).first()
    if bid is None:
        bid = Bid(lot_id=lot.id, buyer_id=buyer.id)
        db.add(bid)
    # A revised bid moves to the back of the tie-break queue.
    bid.rate_paise_per_kg = rate_paise_per_kg
    bid.placed_at = env.now()
    db.flush()
    return bid


def close_auction_if_due(db: Session, env: Env, lot: Lot) -> bool:
    """Sealed-bid close: highest rate wins, earliest bid breaks ties, reserve must be met."""
    if lot.status != LotStatus.LISTED or env.now() < lot.auction_closes_at:
        return False

    bids = list(
        db.scalars(
            select(Bid)
            .where(Bid.lot_id == lot.id)
            .order_by(Bid.rate_paise_per_kg.desc(), Bid.placed_at, Bid.id)
        )
    )
    reserve = lot.reserve_rate_paise_per_kg or 0
    winner = bids[0] if bids and bids[0].rate_paise_per_kg >= reserve else None

    if winner is None:
        lot.status = LotStatus.UNSOLD
        payload = {"result": "unsold", "bid_count": len(bids)}
    else:
        lot.status = LotStatus.AWARDED
        lot.awarded_buyer_id = winner.buyer_id
        lot.awarded_rate_paise_per_kg = winner.rate_paise_per_kg
        payload = {
            "result": "awarded",
            "bid_count": len(bids),
            "buyer_id": str(winner.buyer_id),
            "rate_paise_per_kg": winner.rate_paise_per_kg,
        }
    _record(db, env, lot, "auction.closed", payload, None)
    return True


# --- escrow ----------------------------------------------------------------------------------


def escrow_required(env: Env, lot: Lot) -> int:
    return pricing.escrow_amount(
        lot.awarded_rate_paise_per_kg,
        lot.declared_weight_grams,
        env.settings.escrow_weight_tolerance,
    )


def start_escrow(db: Session, env: Env, buyer: User, lot: Lot) -> PaymentIntent:
    _require_awarded_buyer(lot, buyer)
    _require_status(lot, LotStatus.AWARDED)
    pending = db.scalars(
        select(PaymentIntent).where(
            PaymentIntent.lot_id == lot.id,
            PaymentIntent.buyer_id == buyer.id,
            PaymentIntent.status == PaymentStatus.CREATED,
        )
    ).first()
    if pending is not None:
        return pending

    amount = escrow_required(env, lot)
    intent = PaymentIntent(
        lot_id=lot.id,
        buyer_id=buyer.id,
        amount_paise=amount,
        status=PaymentStatus.CREATED,
        gateway=env.gateway.name,
        gateway_order_id=env.gateway.create_order(amount, receipt=lot.id.hex),
        created_at=env.now(),
    )
    db.add(intent)
    db.flush()
    return intent


def capture_payment(
    db: Session, env: Env, intent: PaymentIntent, *, gateway_payment_id: str, amount_paise: int
) -> PaymentIntent:
    """Idempotent: webhooks are retried, so a second delivery of the same capture is a no-op."""
    if intent.status == PaymentStatus.CAPTURED:
        return intent
    if amount_paise != intent.amount_paise:
        raise Conflict("captured amount does not match the escrow order")
    lot = load_lot(db, intent.lot_id, for_update=True)
    _require_status(lot, LotStatus.AWARDED)

    ledger.post_transaction(
        db,
        kind="escrow_funding",
        idempotency_key=f"fund:{intent.id}",
        lot_id=lot.id,
        now=env.now(),
        postings=[
            (ledger.gateway_account(db), -amount_paise),
            (ledger.escrow_account(db, lot.id), amount_paise),
        ],
    )
    intent.status = PaymentStatus.CAPTURED
    intent.gateway_payment_id = gateway_payment_id
    intent.captured_at = env.now()
    lot.status = LotStatus.FUNDED
    _record(
        db,
        env,
        lot,
        "escrow.funded",
        {
            "amount_paise": amount_paise,
            "gateway": intent.gateway,
            "gateway_payment_id": gateway_payment_id,
        },
        db.get(User, intent.buyer_id),
    )
    return intent


# --- fulfilment and settlement ---------------------------------------------------------------


def schedule_pickup(db: Session, env: Env, actor: User, lot: Lot, *, pickup_at: datetime) -> Lot:
    if not (is_seller_side(lot, actor) or lot.awarded_buyer_id == actor.id):
        raise Forbidden("only the seller or the winning buyer can schedule pickup")
    _require_status(lot, LotStatus.FUNDED, LotStatus.PICKUP_SCHEDULED)
    if pickup_at <= env.now():
        raise Invalid("pickup must be in the future")
    lot.pickup_at = pickup_at
    lot.status = LotStatus.PICKUP_SCHEDULED
    _record(db, env, lot, "pickup.scheduled", {"pickup_at": pickup_at.isoformat()}, actor)
    return lot


def record_delivery(
    db: Session,
    env: Env,
    buyer: User,
    lot: Lot,
    *,
    measured_weight_grams: int,
    slip: bytes,
    slip_content_type: str | None,
) -> Lot:
    _require_awarded_buyer(lot, buyer)
    _require_status(lot, LotStatus.PICKUP_SCHEDULED)
    if not 0 < measured_weight_grams <= MAX_WEIGHT_GRAMS:
        raise Invalid("measured weight must be between 1 g and 100 tonnes")
    extension = _check_image(slip, slip_content_type)
    digest = hashlib.sha256(slip).hexdigest()

    lot.measured_weight_grams = measured_weight_grams
    lot.weighbridge_slip_key = env.storage.put("weighbridge", slip, extension)
    lot.weighbridge_slip_sha256 = digest
    lot.status = LotStatus.DELIVERED
    _record(
        db,
        env,
        lot,
        "delivery.recorded",
        {
            "declared_weight_grams": lot.declared_weight_grams,
            "measured_weight_grams": measured_weight_grams,
            "weighbridge_slip_sha256": digest,
        },
        buyer,
    )
    return lot


def accept_delivery(db: Session, env: Env, actor: User, lot: Lot) -> Lot:
    """Seller agrees with the weighbridge reading; escrow settles against the measured weight."""
    _require_seller_side(lot, actor)
    _require_status(lot, LotStatus.DELIVERED)

    payable = pricing.amount_for(lot.awarded_rate_paise_per_kg, lot.measured_weight_grams)
    escrow = ledger.escrow_account(db, lot.id)
    held = ledger.balance(db, escrow)
    _record(
        db,
        env,
        lot,
        "delivery.accepted",
        {"measured_weight_grams": lot.measured_weight_grams, "payable_paise": payable},
        actor,
    )

    if payable > held:
        # Weighbridge reading exceeds the escrowed tolerance: the buyer owes more than is held.
        lot.status = LotStatus.DISPUTED
        _record(
            db,
            env,
            lot,
            "settlement.blocked",
            {"reason": "payable_exceeds_escrow", "payable_paise": payable, "escrowed_paise": held},
            None,
        )
        return lot

    refund = held - payable
    ledger.post_transaction(
        db,
        kind="settlement",
        idempotency_key=f"settle:{lot.id}",
        lot_id=lot.id,
        now=env.now(),
        postings=[
            (escrow, -held),
            (ledger.wallet_account(db, lot.seller_id), payable),
            (ledger.wallet_account(db, lot.awarded_buyer_id), refund),
        ],
    )
    lot.settled_amount_paise = payable
    lot.status = LotStatus.SETTLED
    _record(
        db,
        env,
        lot,
        "settlement.completed",
        {
            "rate_paise_per_kg": lot.awarded_rate_paise_per_kg,
            "measured_weight_grams": lot.measured_weight_grams,
            "paid_to_seller_paise": payable,
            "refunded_to_buyer_paise": refund,
        },
        None,
    )
    issue_certificate(db, env, lot)
    return lot


def dispute_delivery(db: Session, env: Env, actor: User, lot: Lot, *, reason: str) -> Lot:
    _require_seller_side(lot, actor)
    _require_status(lot, LotStatus.DELIVERED)
    lot.status = LotStatus.DISPUTED
    _record(db, env, lot, "delivery.disputed", {"reason": reason}, actor)
    return lot
