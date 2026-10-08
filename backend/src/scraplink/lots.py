"""Lot lifecycle — the single trade path of the first slice.

    DRAFT --confirm--> DRAFT --list--> LISTED --close--> AWARDED | UNSOLD
                                       LISTED --seller accepts an open bid--> AWARDED
    AWARDED --not paid by escrow_due_at, or declined--> AWARDED (next bid) | UNSOLD
    AWARDED --escrow captured--> FUNDED --pickup--> PICKUP_SCHEDULED
    PICKUP_SCHEDULED --weighbridge--> DELIVERED --seller accepts--> SETTLED (+ certificate)
                                               --seller disputes, or payable > escrow--> DISPUTED
    DISPUTED --admin settles at an agreed weight--> SETTLED (+ certificate)
             --admin cancels--> CANCELLED (escrow back to the buyer)

Every transition appends a custody event in the same database transaction as the state
change, so the chain and the lot can never disagree. The people a step concerns are notified
in the same transaction (notifications.py).
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import compliance, custody, invoices, ledger, places, pricing
from .certificates import issue_certificate
from .env import Env
from .errors import Conflict, Forbidden, Invalid, NotFound
from .models import (
    AuctionFormat,
    Bid,
    CustodyEvent,
    KycStatus,
    Lot,
    LotStatus,
    Material,
    PaymentIntent,
    PaymentStatus,
    ReferenceRate,
    Role,
    Transporter,
    User,
)
from .notifications import kilos, notify, rupees
from .routing import IST

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_WEIGHT_GRAMS = 100_000_000  # 100 tonnes
# In an open auction a new bid must beat the best one by at least this much.
OPEN_BID_STEP_PAISE = 100  # ₹1 per kg


# --- helpers ---------------------------------------------------------------------------------


def _record(db: Session, env: Env, lot: Lot, event_type: str, payload: dict, actor: User | None):
    custody.append_event(db, lot, event_type, payload, actor=actor, now=env.now())


def _what(lot: Lot) -> str:
    """ "copper lot", "steel - heavy melting scrap (HMS 1 & 2) lot": acronyms keep their case."""
    if lot.material is None:
        return "lot"
    name = lot.material.name
    if name[1:2].islower():
        name = name[0].lower() + name[1:]
    return f"{name} lot"


def _when(moment: datetime) -> str:
    local = moment.astimezone(IST)
    return (
        f"{local.day} {local:%b}, {local:%I:%M} {local:%p}".replace(", 0", ", ")
        .replace("AM", "am")
        .replace("PM", "pm")
    )


def _who(user: User) -> str:
    return user.business_name or user.name


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


def _require_current_winner(db: Session, lot: Lot, user: User) -> None:
    """As _require_awarded_buyer, but a buyer whose win has lapsed is told so, not that they
    never won: their page may still show the award from before the deadline."""
    if lot.awarded_buyer_id != user.id:
        lapsed = db.scalars(
            select(Bid.id).where(
                Bid.lot_id == lot.id, Bid.buyer_id == user.id, Bid.lapsed_at.is_not(None)
            )
        ).first()
        if lapsed is not None:
            raise Conflict("your win on this lot has lapsed, so it passed to the next bidder")
    _require_awarded_buyer(lot, user)


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
        # Refresh under the lock: the session may hold a copy read before another writer.
        query = query.with_for_update().execution_options(populate_existing=True)
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


def grade_suggestion_is_confident(db: Session, env: Env, lot: Lot) -> bool:
    """A grade is only prefilled alongside a confident material, and on its own confidence."""
    return (
        suggestion_is_confident(db, env, lot)
        and lot.suggested_grade is not None
        and lot.suggested_grade_confidence is not None
        and lot.suggested_grade_confidence >= env.settings.ml_classification_confidence_threshold
    )


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
        lot.suggested_grade_confidence = suggestion.grade_confidence
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
                "grade_confidence": None
                if suggestion.grade_confidence is None
                else f"{suggestion.grade_confidence:.4f}",
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
    place: str | None = None,
    pickup_ready_on: date | None = None,
) -> Lot:
    """The human verification step: the seller states what the lot is, where it is and when it
    can be collected. The estimate allows for the distance from the yard."""
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
    location_bp = None
    if place is not None:
        where = places.PLACES.get(place)
        if where is None:
            raise Invalid(f"unknown place '{place}'")
        depot = (env.settings.depot_latitude, env.settings.depot_longitude)
        location_bp = pricing.location_adjustment_bp(
            places.km_from(where, depot),
            env.settings.freight_bp_per_10_km,
            env.settings.freight_max_bp,
        )
    if pickup_ready_on is not None and pickup_ready_on < env.now().astimezone(IST).date():
        raise Invalid("the day it's ready for pickup can't be in the past")

    estimate = pricing.estimate(
        rate.rate_paise_per_kg,
        grade,
        declared_weight_grams,
        env.settings.price_band,
        location_bp or 0,
    )
    lot.material_id = material.id
    lot.material = material
    lot.grade = grade
    lot.declared_weight_grams = declared_weight_grams
    lot.place = place
    lot.pickup_ready_on = pickup_ready_on
    lot.location_adjustment_bp = location_bp
    lot.reference_rate_paise_per_kg = rate.rate_paise_per_kg
    lot.reference_rate_id = rate.id
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
            "place": place,
            "pickup_ready_on": pickup_ready_on.isoformat() if pickup_ready_on else None,
            "location_adjustment_bp": location_bp,
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
    auction_format: str = AuctionFormat.SEALED,
) -> Lot:
    _require_seller_side(lot, actor)
    _require_status(lot, LotStatus.DRAFT)
    if lot.material_id is None:
        raise Conflict("confirm the material, grade and weight before listing")
    if not 1 <= auction_hours <= 168:
        raise Invalid("auctions run between 1 hour and 7 days")
    if auction_format not in tuple(AuctionFormat):
        raise Invalid("auction format must be sealed or open")

    lot.status = LotStatus.LISTED
    lot.auction_closes_at = env.now() + timedelta(hours=auction_hours)
    lot.reserve_rate_paise_per_kg = reserve_rate_paise_per_kg
    lot.auction_format = auction_format
    _record(
        db,
        env,
        lot,
        "lot.listed",
        {
            "auction_closes_at": lot.auction_closes_at.isoformat(),
            "reserve_rate_paise_per_kg": reserve_rate_paise_per_kg,
            "auction_format": auction_format,
        },
        actor,
    )
    return lot


def best_bid(db: Session, lot: Lot) -> Bid | None:
    """Highest rate, earliest bid breaks ties, lapsed wins excluded."""
    return db.scalars(
        select(Bid)
        .where(Bid.lot_id == lot.id, Bid.lapsed_at.is_(None))
        .order_by(Bid.rate_paise_per_kg.desc(), Bid.placed_at, Bid.id)
        .limit(1)
    ).first()


def place_bid(db: Session, env: Env, buyer: User, lot: Lot, *, rate_paise_per_kg: int) -> Bid:
    if buyer.role != Role.BUYER:
        raise Forbidden("only buyers can bid")
    _require_approved(buyer, "your")
    _require_status(lot, LotStatus.LISTED)
    if env.now() >= lot.auction_closes_at:
        raise Conflict("bidding on this lot has closed")
    if rate_paise_per_kg <= 0:
        raise Invalid("bid rate must be positive")
    compliance.require_authorised(buyer, lot.material)
    leader = best_bid(db, lot) if lot.auction_format == AuctionFormat.OPEN else None
    if leader is not None and rate_paise_per_kg < leader.rate_paise_per_kg + OPEN_BID_STEP_PAISE:
        floor = rupees(leader.rate_paise_per_kg + OPEN_BID_STEP_PAISE)
        raise Invalid(f"bid at least {floor}/kg to beat the best bid")

    bid = db.scalars(select(Bid).where(Bid.lot_id == lot.id, Bid.buyer_id == buyer.id)).first()
    if bid is None:
        bid = Bid(lot_id=lot.id, buyer_id=buyer.id)
        db.add(bid)
    # A revised bid moves to the back of the tie-break queue.
    bid.rate_paise_per_kg = rate_paise_per_kg
    bid.placed_at = env.now()
    db.flush()
    seller = db.get(User, lot.seller_id)
    if lot.auction_format == AuctionFormat.OPEN:
        rate = rupees(rate_paise_per_kg)
        notify(db, env, seller, f"New bid of {rate}/kg on your {_what(lot)}.", kind="bid", lot=lot)
        if leader is not None and leader.buyer_id != buyer.id:
            notify(
                db,
                env,
                db.get(User, leader.buyer_id),
                f"You've been outbid on the {_what(lot)}: the best bid is now {rate}/kg.",
                kind="outbid",
                lot=lot,
            )
    else:
        text = f"A buyer bid on your {_what(lot)}. Bids stay sealed until bidding closes."
        notify(db, env, seller, text, kind="bid", lot=lot)
    return bid


def _award_next_bid(db: Session, env: Env, lot: Lot) -> dict:
    """Award the best bid that hasn't lapsed: highest rate, earliest bid breaks ties, reserve
    must be met. With none left the lot is unsold. Returns the outcome for the custody event."""
    best = best_bid(db, lot)
    if best is None or best.rate_paise_per_kg < (lot.reserve_rate_paise_per_kg or 0):
        lot.status = LotStatus.UNSOLD
        lot.awarded_buyer_id = None
        lot.awarded_rate_paise_per_kg = None
        lot.escrow_due_at = None
        text = f"Bidding on your {_what(lot)} closed without a bid at your price, so it is unsold."
        notify(db, env, db.get(User, lot.seller_id), text, kind="unsold", lot=lot)
        return {"result": "unsold"}
    return _award(db, env, lot, best)


def _award(db: Session, env: Env, lot: Lot, bid: Bid) -> dict:
    lot.status = LotStatus.AWARDED
    lot.awarded_buyer_id = bid.buyer_id
    lot.awarded_rate_paise_per_kg = bid.rate_paise_per_kg
    lot.escrow_due_at = env.now() + timedelta(hours=env.settings.escrow_funding_hours)
    buyer, rate = db.get(User, bid.buyer_id), rupees(bid.rate_paise_per_kg)
    pay = rupees(escrow_required(env, lot))
    notify(
        db,
        env,
        buyer,
        f"You won the {_what(lot)} at {rate}/kg. Pay {pay} into escrow by "
        f"{_when(lot.escrow_due_at)}.",
        kind="won",
        lot=lot,
    )
    notify(
        db,
        env,
        db.get(User, lot.seller_id),
        f"Your {_what(lot)} went to {_who(buyer)} at {rate}/kg. Waiting for their payment.",
        kind="sold",
        lot=lot,
    )
    return {
        "result": "awarded",
        "buyer_id": str(bid.buyer_id),
        "rate_paise_per_kg": bid.rate_paise_per_kg,
        "escrow_due_at": lot.escrow_due_at.isoformat(),
    }


def accept_bid(db: Session, env: Env, seller: User, lot: Lot, *, bid_id: int) -> Lot:
    """In an open auction the seller can take a bid before bidding closes."""
    _require_seller_side(lot, seller)
    _require_status(lot, LotStatus.LISTED)
    if lot.auction_format != AuctionFormat.OPEN:
        raise Conflict("sealed bids are opened when bidding closes, and the best one wins")
    bid = db.get(Bid, bid_id)
    if bid is None or bid.lot_id != lot.id or bid.lapsed_at is not None:
        raise NotFound("bid not found")
    bid_count = db.scalar(select(func.count()).select_from(Bid).where(Bid.lot_id == lot.id))
    payload = {"bid_count": bid_count, **_award(db, env, lot, bid)}
    _record(db, env, lot, "auction.accepted", payload, seller)
    return lot


def close_auction_if_due(db: Session, env: Env, lot: Lot) -> bool:
    """Sealed-bid close: the best bid that meets the reserve wins."""
    if lot.status != LotStatus.LISTED or env.now() < lot.auction_closes_at:
        return False
    bid_count = db.scalar(select(func.count()).select_from(Bid).where(Bid.lot_id == lot.id))
    payload = {"bid_count": bid_count, **_award_next_bid(db, env, lot)}
    _record(db, env, lot, "auction.closed", payload, None)
    return True


def award_lapse_due(env: Env, lot: Lot) -> bool:
    return (
        lot.status == LotStatus.AWARDED
        and lot.escrow_due_at is not None
        and env.now() >= lot.escrow_due_at
    )


def lapse_award_if_due(db: Session, env: Env, lot: Lot) -> bool:
    """The winner didn't pay in time: the lot passes to the next bid, or ends unsold."""
    if not award_lapse_due(env, lot):
        return False
    _lapse_award(db, env, lot, reason="not_paid", actor=None)
    return True


def decline_award(db: Session, env: Env, buyer: User, lot: Lot) -> Lot:
    """The winner says they can't buy, so the seller doesn't wait out the deadline."""
    _require_current_winner(db, lot, buyer)
    _require_status(lot, LotStatus.AWARDED)
    _lapse_award(db, env, lot, reason="declined", actor=buyer)
    return lot


def _lapse_award(db: Session, env: Env, lot: Lot, *, reason: str, actor: User | None) -> None:
    bid = db.scalars(
        select(Bid).where(Bid.lot_id == lot.id, Bid.buyer_id == lot.awarded_buyer_id)
    ).one()
    bid.lapsed_at = env.now()
    payload = {
        "reason": reason,
        "lapsed_buyer_id": str(bid.buyer_id),
        "lapsed_rate_paise_per_kg": bid.rate_paise_per_kg,
        **_award_next_bid(db, env, lot),
    }
    _record(db, env, lot, "award.lapsed", payload, actor)


# --- escrow ----------------------------------------------------------------------------------


def escrow_required(env: Env, lot: Lot) -> int:
    return pricing.escrow_amount(
        lot.awarded_rate_paise_per_kg,
        lot.declared_weight_grams,
        env.settings.escrow_weight_tolerance,
    )


def start_escrow(db: Session, env: Env, buyer: User, lot: Lot) -> PaymentIntent:
    _require_current_winner(db, lot, buyer)
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
    # The deadline holds even if nobody has looked at the lot since it passed.
    lapse_award_if_due(db, env, lot)
    if lot.status != LotStatus.AWARDED or lot.awarded_buyer_id != intent.buyer_id:
        return _return_late_payment(db, env, intent, lot, gateway_payment_id=gateway_payment_id)

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
    notify(
        db,
        env,
        db.get(User, lot.seller_id),
        f"{_who(db.get(User, intent.buyer_id))} paid {rupees(amount_paise)} into escrow for your "
        f"{_what(lot)}. Book the pickup.",
        kind="funded",
        lot=lot,
    )
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


def _return_late_payment(
    db: Session, env: Env, intent: PaymentIntent, lot: Lot, *, gateway_payment_id: str
) -> PaymentIntent:
    """The rail took money for an award that has since lapsed (a checkout completed after the
    deadline, or a webhook arrived late). It must not fund someone else's trade, and it must
    not vanish: it goes to the payer's wallet, and the lot's record says so."""
    buyer = db.get(User, intent.buyer_id)
    ledger.post_transaction(
        db,
        kind="late_payment_returned",
        idempotency_key=f"late:{intent.id}",
        lot_id=lot.id,
        now=env.now(),
        postings=[
            (ledger.gateway_account(db), -intent.amount_paise),
            (ledger.wallet_account(db, buyer.id), intent.amount_paise),
        ],
    )
    intent.status = PaymentStatus.CAPTURED
    intent.gateway_payment_id = gateway_payment_id
    intent.captured_at = env.now()
    _record(
        db,
        env,
        lot,
        "payment.returned",
        {
            "reason": "award_no_longer_held",
            "buyer_id": str(buyer.id),
            "amount_paise": intent.amount_paise,
            "gateway_payment_id": gateway_payment_id,
        },
        buyer,
    )
    return intent


# --- fulfilment and settlement ---------------------------------------------------------------


def schedule_pickup(
    db: Session,
    env: Env,
    actor: User,
    lot: Lot,
    *,
    pickup_at: datetime,
    location: tuple[float, float] | None = None,
) -> Lot:
    if not (is_seller_side(lot, actor) or lot.awarded_buyer_id == actor.id):
        raise Forbidden("only the seller or the winning buyer can schedule pickup")
    _require_status(lot, LotStatus.FUNDED, LotStatus.PICKUP_SCHEDULED)
    if pickup_at <= env.now():
        raise Invalid("pickup must be in the future")
    lot.pickup_at = pickup_at
    lot.status = LotStatus.PICKUP_SCHEDULED
    payload: dict = {"pickup_at": pickup_at.isoformat()}
    if location is not None:
        lot.pickup_latitude, lot.pickup_longitude = location
        # As strings, like every other number in the chain that isn't an integer.
        payload["location"] = {"latitude": f"{location[0]:.6f}", "longitude": f"{location[1]:.6f}"}
    _record(db, env, lot, "pickup.scheduled", payload, actor)
    other = lot.awarded_buyer_id if is_seller_side(lot, actor) else lot.seller_id
    text = f"{_who(actor)} booked the pickup of the {_what(lot)} for {_when(pickup_at)}."
    notify(db, env, db.get(User, other), text, kind="pickup", lot=lot)
    return lot


def assign_transporter(
    db: Session, env: Env, admin: User | None, lot: Lot, *, transporter_id: int
) -> Lot:
    """`admin` is None only when operations tooling (the demo seeder) assigns one."""
    if admin is not None and admin.role != Role.ADMIN:
        raise Forbidden("only an admin can assign a transporter")
    _require_status(lot, LotStatus.FUNDED, LotStatus.PICKUP_SCHEDULED)
    transporter = db.get(Transporter, transporter_id)
    if transporter is None:
        raise NotFound("transporter not found")
    lot.transporter = transporter
    lot.transporter_id = transporter.id
    _record(
        db,
        env,
        lot,
        "pickup.transporter_assigned",
        {
            "transporter_id": transporter.id,
            "name": transporter.name,
            "vehicle": transporter.vehicle,
        },
        admin,
    )
    text = f"{transporter.name} ({transporter.vehicle}) will collect the {_what(lot)}."
    for user_id in (lot.seller_id, lot.awarded_buyer_id):
        notify(db, env, db.get(User, user_id), text, kind="transporter", lot=lot)
    return lot


def record_pickup_weight(db: Session, env: Env, actor: User, lot: Lot, *, weight_grams: int):
    """The seller's reading as the truck is loaded. Kept beside the weighbridge reading at
    delivery, so a gap between the two shows; the weighbridge still settles the trade."""
    if not (is_seller_side(lot, actor) or actor.role == Role.ADMIN):
        raise Forbidden("only the seller can record the weight at pickup")
    _require_status(lot, LotStatus.PICKUP_SCHEDULED)
    if not 0 < weight_grams <= MAX_WEIGHT_GRAMS:
        raise Invalid("the weight must be between 1 g and 100 tonnes")
    lot.pickup_weight_grams = weight_grams
    _record(
        db,
        env,
        lot,
        "pickup.weighed",
        {"pickup_weight_grams": weight_grams, "declared_weight_grams": lot.declared_weight_grams},
        actor,
    )
    text = f"The seller weighed {kilos(weight_grams)} as the {_what(lot)} was loaded."
    notify(db, env, db.get(User, lot.awarded_buyer_id), text, kind="pickup_weight", lot=lot)
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
    notify(
        db,
        env,
        db.get(User, lot.seller_id),
        f"{_who(buyer)} recorded {kilos(measured_weight_grams)} at the weighbridge for your "
        f"{_what(lot)}. Check it, then accept or dispute.",
        kind="delivered",
        lot=lot,
    )
    return lot


def accept_delivery(db: Session, env: Env, actor: User, lot: Lot) -> Lot:
    """Seller agrees with the weighbridge reading; escrow settles against the measured weight."""
    _require_seller_side(lot, actor)
    _require_status(lot, LotStatus.DELIVERED)

    payable = pricing.amount_for(lot.awarded_rate_paise_per_kg, lot.measured_weight_grams)
    held = ledger.balance(db, ledger.escrow_account(db, lot.id))
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
        text = (
            f"The weighbridge reading for the {_what(lot)} costs more than escrow holds. "
            "An admin will resolve it."
        )
        for user_id in (lot.seller_id, lot.awarded_buyer_id):
            notify(db, env, db.get(User, user_id), text, kind="dispute", lot=lot)
        return lot

    _settle(db, env, lot, payable=payable, held=held)
    return lot


def _settle(db: Session, env: Env, lot: Lot, *, payable: int, held: int) -> None:
    """Pay the seller `payable` from escrow, return the rest to the buyer, issue the certificate."""
    refund = held - payable
    ledger.post_transaction(
        db,
        kind="settlement",
        idempotency_key=f"settle:{lot.id}",
        lot_id=lot.id,
        now=env.now(),
        postings=[
            (ledger.escrow_account(db, lot.id), -held),
            (ledger.wallet_account(db, lot.seller_id), payable),
            (ledger.wallet_account(db, lot.awarded_buyer_id), refund),
        ],
    )
    lot.settled_amount_paise = payable
    lot.status = LotStatus.SETTLED
    payload = {
        "rate_paise_per_kg": lot.awarded_rate_paise_per_kg,
        "measured_weight_grams": lot.measured_weight_grams,
        "paid_to_seller_paise": payable,
        "refunded_to_buyer_paise": refund,
    }
    if lot.settled_weight_grams is not None:
        payload["settled_weight_grams"] = lot.settled_weight_grams
    _record(db, env, lot, "settlement.completed", payload, None)
    issue_certificate(db, env, lot)
    invoice = invoices.issue_invoice(db, lot, env.now())
    notify(
        db,
        env,
        db.get(User, lot.seller_id),
        f"You were paid {rupees(payable)} for your {_what(lot)}. Invoice {invoice.number} and "
        "the certificate are ready.",
        kind="settled",
        lot=lot,
    )
    back = f" {rupees(refund)} of your escrow came back to your wallet." if refund else ""
    notify(
        db,
        env,
        db.get(User, lot.awarded_buyer_id),
        f"The {_what(lot)} trade is settled.{back} Invoice {invoice.number} is ready.",
        kind="settled",
        lot=lot,
    )


def dispute_delivery(db: Session, env: Env, actor: User, lot: Lot, *, reason: str) -> Lot:
    _require_seller_side(lot, actor)
    _require_status(lot, LotStatus.DELIVERED)
    lot.status = LotStatus.DISPUTED
    _record(db, env, lot, "delivery.disputed", {"reason": reason}, actor)
    text = (
        f"The seller disputed the weighbridge reading for the {_what(lot)}. "
        "An admin will resolve it."
    )
    notify(db, env, db.get(User, lot.awarded_buyer_id), text, kind="dispute", lot=lot)
    return lot


# --- dispute resolution ----------------------------------------------------------------------


@dataclass(frozen=True)
class DisputeDetails:
    # "seller" when the seller rejected the weighbridge reading; "escrow" when the reading cost
    # more than the buyer had paid into escrow, so settlement stopped on its own.
    raised_by: str
    reason: str
    raised_at: str


def dispute_details(db: Session, lot: Lot) -> DisputeDetails | None:
    if lot.status != LotStatus.DISPUTED:
        return None
    event = db.scalars(
        select(CustodyEvent)
        .where(
            CustodyEvent.lot_id == lot.id,
            CustodyEvent.event_type.in_(("delivery.disputed", "settlement.blocked")),
        )
        .order_by(CustodyEvent.seq.desc())
        .limit(1)
    ).first()
    if event is None:
        return None
    if event.event_type == "delivery.disputed":
        return DisputeDetails("seller", event.payload["reason"], event.recorded_at)
    return DisputeDetails(
        "escrow",
        "The weighbridge reading costs more than the buyer paid into escrow.",
        event.recorded_at,
    )


def max_settle_weight_grams(lot: Lot, held_paise: int) -> int:
    """The heaviest weight the money in escrow pays for in full at the winning rate."""
    return held_paise * 1000 // lot.awarded_rate_paise_per_kg


def resolve_dispute(
    db: Session,
    env: Env,
    admin: User,
    lot: Lot,
    *,
    outcome: str,
    note: str,
    weight_grams: int | None = None,
) -> Lot:
    """An admin closes a dispute: settle at an agreed weight, or cancel and refund the buyer."""
    if admin.role != Role.ADMIN:
        raise Forbidden("only an admin can resolve a dispute")
    _require_status(lot, LotStatus.DISPUTED)
    note = note.strip()
    if len(note) < 3:
        raise Invalid("say how the dispute was resolved; both parties will see it in the record")
    escrow = ledger.escrow_account(db, lot.id)
    held = ledger.balance(db, escrow)

    if outcome == "cancel":
        ledger.post_transaction(
            db,
            kind="dispute_refund",
            idempotency_key=f"dispute-refund:{lot.id}",
            lot_id=lot.id,
            now=env.now(),
            postings=[(escrow, -held), (ledger.wallet_account(db, lot.awarded_buyer_id), held)],
        )
        lot.status = LotStatus.CANCELLED
        _record(
            db,
            env,
            lot,
            "dispute.resolved",
            {"outcome": "cancelled", "refunded_to_buyer_paise": held, "note": note},
            admin,
        )
        text = (
            f"The {_what(lot)} trade was cancelled. {rupees(held)} went back to the buyer's wallet."
        )
        for user_id in (lot.seller_id, lot.awarded_buyer_id):
            notify(db, env, db.get(User, user_id), text, kind="dispute", lot=lot)
        return lot

    if outcome != "settle":
        raise Invalid("outcome must be settle or cancel")
    if weight_grams is None or not 0 < weight_grams <= MAX_WEIGHT_GRAMS:
        raise Invalid("give the weight to settle at, between 1 g and 100 tonnes")
    payable = pricing.amount_for(lot.awarded_rate_paise_per_kg, weight_grams)
    if payable > held:
        most = max_settle_weight_grams(lot, held)
        raise Conflict(
            f"that weight costs more than the buyer paid into escrow; settle at "
            f"{most / 1000:g} kg or less, or cancel"
        )
    lot.settled_weight_grams = weight_grams
    _record(
        db,
        env,
        lot,
        "dispute.resolved",
        {
            "outcome": "settled",
            "weighbridge_weight_grams": lot.measured_weight_grams,
            "settled_weight_grams": weight_grams,
            "note": note,
        },
        admin,
    )
    _settle(db, env, lot, payable=payable, held=held)
    return lot
