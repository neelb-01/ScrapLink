"""Persistence model.

Money is integer paise and weight is integer grams throughout, so no arithmetic in the
trade path ever touches a float.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    TypeDecorator,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class UTCDateTime(TypeDecorator):
    """Stores naive UTC, returns aware UTC — identical behaviour on SQLite and PostgreSQL."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to UTCDateTime")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return None if value is None else value.replace(tzinfo=UTC)


class Role(StrEnum):
    SELLER = "seller"
    BUYER = "buyer"
    ADMIN = "admin"


class KycStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LotStatus(StrEnum):
    DRAFT = "draft"
    LISTED = "listed"
    AWARDED = "awarded"
    UNSOLD = "unsold"
    FUNDED = "funded"
    PICKUP_SCHEDULED = "pickup_scheduled"
    DELIVERED = "delivered"
    SETTLED = "settled"
    DISPUTED = "disputed"
    # A dispute was resolved by refunding the buyer; the material stays with the seller.
    CANCELLED = "cancelled"


class RateSource(StrEnum):
    SEED = "seed"  # the starting catalogue
    ADMIN = "admin"  # set by hand on the admin prices screen
    MARKET = "market"  # moved by the reprice job toward what recent trades paid


class PaymentStatus(StrEnum):
    CREATED = "created"
    CAPTURED = "captured"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(16))
    business_name: Mapped[str | None] = mapped_column(String(200))
    gstin: Mapped[str | None] = mapped_column(String(15))
    pan: Mapped[str | None] = mapped_column(String(10))
    kyc_status: Mapped[str] = mapped_column(String(16), default=KycStatus.PENDING)
    kyc_note: Mapped[str | None] = mapped_column(String(500))
    # Comma-separated codes from compliance.AUTHORISATIONS, recorded by an admin at approval.
    authorisations: Mapped[str] = mapped_column(String(100), default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    family: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(500), default="")
    # Set for regulated waste: only buyers holding this authorisation may bid on or request it.
    authorisation: Mapped[str | None] = mapped_column(String(20))


class ReferenceRate(Base):
    """Market reference for a material at grade A. History is kept, never edited.

    Each row says why it exists, so a seller can be told why the price moved: the starting
    catalogue, an admin, or the reprice job (pricing.market_move) with the trades behind it.
    """

    __tablename__ = "reference_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    rate_paise_per_kg: Mapped[int] = mapped_column(BigInteger)
    effective_from: Mapped[datetime] = mapped_column(UTCDateTime())
    set_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(
        String(12), default=RateSource.ADMIN, server_default=RateSource.ADMIN
    )
    # The rate this one replaced; empty for a material's first rate.
    previous_rate_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    # Market rates only: how many paid trades, over how many days, and their median price
    # converted to grade A. `capped` is set when the move was held to the per-run limit.
    trade_count: Mapped[int | None] = mapped_column(Integer)
    window_days: Mapped[int | None] = mapped_column(Integer)
    market_median_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    capped: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())


class Lot(Base):
    __tablename__ = "lots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(24), default=LotStatus.DRAFT, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())

    photo_key: Mapped[str] = mapped_column(String(300))
    photo_sha256: Mapped[str] = mapped_column(String(64))

    # Raw model output, kept even when it was below threshold or rejected by the seller.
    suggested_material_code: Mapped[str | None] = mapped_column(String(40))
    suggested_grade: Mapped[str | None] = mapped_column(String(1))
    suggestion_confidence: Mapped[float | None] = mapped_column(Float)

    # What the seller confirmed.
    material_id: Mapped[int | None] = mapped_column(ForeignKey("materials.id"))
    grade: Mapped[str | None] = mapped_column(String(1))
    declared_weight_grams: Mapped[int | None] = mapped_column(BigInteger)

    reference_rate_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    # The rate row the estimate used, so the seller can be told why it was that price.
    reference_rate_id: Mapped[int | None] = mapped_column(ForeignKey("reference_rates.id"))
    estimate_rate_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    estimate_total_paise: Mapped[int | None] = mapped_column(BigInteger)
    estimate_low_paise: Mapped[int | None] = mapped_column(BigInteger)
    estimate_high_paise: Mapped[int | None] = mapped_column(BigInteger)

    reserve_rate_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    auction_closes_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    awarded_buyer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    awarded_rate_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    # The awarded buyer must fund escrow by this time, or the award lapses to the next bid.
    escrow_due_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    pickup_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    # Where the truck collects from, if the person booking shared it; route planning uses it.
    pickup_latitude: Mapped[float | None] = mapped_column(Float)
    pickup_longitude: Mapped[float | None] = mapped_column(Float)

    measured_weight_grams: Mapped[int | None] = mapped_column(BigInteger)
    weighbridge_slip_key: Mapped[str | None] = mapped_column(String(300))
    weighbridge_slip_sha256: Mapped[str | None] = mapped_column(String(64))

    settled_amount_paise: Mapped[int | None] = mapped_column(BigInteger)
    # Set only when a dispute settled at a weight other than the weighbridge reading.
    settled_weight_grams: Mapped[int | None] = mapped_column(BigInteger)

    seller: Mapped[User] = relationship(foreign_keys=[seller_id])
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    awarded_buyer: Mapped[User | None] = relationship(foreign_keys=[awarded_buyer_id])
    material: Mapped[Material | None] = relationship()
    reference_rate: Mapped[ReferenceRate | None] = relationship()
    certificate: Mapped[Certificate | None] = relationship(back_populates="lot")

    @property
    def billed_weight_grams(self) -> int | None:
        """The weight the trade was paid on: agreed in a dispute, else the weighbridge's."""
        return self.settled_weight_grams or self.measured_weight_grams


class Bid(Base):
    """Sealed bid, expressed per kg so it settles against the weighbridge weight."""

    __tablename__ = "bids"
    __table_args__ = (UniqueConstraint("lot_id", "buyer_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lots.id"), index=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    rate_paise_per_kg: Mapped[int] = mapped_column(BigInteger)
    placed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    # Set when this bid won but the buyer didn't pay in time or declined; it can't win again.
    lapsed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lots.id"), index=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16), default=PaymentStatus.CREATED)
    gateway: Mapped[str] = mapped_column(String(16))
    gateway_order_id: Mapped[str] = mapped_column(String(64), unique=True)
    gateway_payment_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    captured_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class LedgerAccount(Base):
    """`key` is the natural identity: "gateway:inbound", "escrow:<lot>", "wallet:<user>"."""

    __tablename__ = "ledger_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(16))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    lot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lots.id"))


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    lot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lots.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())

    postings: Mapped[list[LedgerPosting]] = relationship(back_populates="transaction")


class LedgerPosting(Base):
    """Signed amount; the postings of every transaction sum to zero."""

    __tablename__ = "ledger_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("ledger_transactions.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("ledger_accounts.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger)

    transaction: Mapped[LedgerTransaction] = relationship(back_populates="postings")


class CustodyEvent(Base):
    """One link in a lot's append-only SHA-256 chain. Rows are never updated or deleted."""

    __tablename__ = "custody_events"
    __table_args__ = (UniqueConstraint("lot_id", "seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lots.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    # Kept as the exact ISO string that was hashed, so no datetime round-trip can alter it.
    recorded_at: Mapped[str] = mapped_column(String(40))
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lots.id"), unique=True)
    head_hash: Mapped[str] = mapped_column(String(64))
    event_count: Mapped[int] = mapped_column(Integer)
    pdf_key: Mapped[str] = mapped_column(String(300))
    pdf_sha256: Mapped[str] = mapped_column(String(64))
    issued_at: Mapped[datetime] = mapped_column(UTCDateTime())

    lot: Mapped[Lot] = relationship(back_populates="certificate")


# --- Started modules: each is a first slice, not the finished capability. -------------------


class RfqStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class Rfq(Base):
    """A buyer's request for quotation: the material and quantity they want sellers to offer."""

    __tablename__ = "rfqs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    quantity_grams: Mapped[int] = mapped_column(BigInteger)
    target_rate_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    needed_by: Mapped[datetime] = mapped_column(UTCDateTime())
    note: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(16), default=RfqStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())

    buyer: Mapped[User] = relationship()
    material: Mapped[Material] = relationship()


class AgreementStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    DECLINED = "declined"


class SupplyAgreement(Base):
    """A buyer's standing offer to take a fixed monthly quantity from a seller at a fixed rate."""

    __tablename__ = "supply_agreements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    monthly_quantity_grams: Mapped[int] = mapped_column(BigInteger)
    rate_paise_per_kg: Mapped[int] = mapped_column(BigInteger)
    starts_on: Mapped[date] = mapped_column(Date)
    months: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default=AgreementStatus.PROPOSED)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    buyer: Mapped[User] = relationship(foreign_keys=[buyer_id])
    seller: Mapped[User] = relationship(foreign_keys=[seller_id])
    material: Mapped[Material] = relationship()


class Transporter(Base):
    """A logistics partner who can be sent to collect lots."""

    __tablename__ = "transporters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(16))
    vehicle: Mapped[str] = mapped_column(String(120))
    capacity_grams: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class CustodyAnchor(Base):
    """A Merkle root over a contiguous run of custody events, sealing them as a batch."""

    __tablename__ = "custody_anchors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_event_id: Mapped[int] = mapped_column(Integer)
    last_event_id: Mapped[int] = mapped_column(Integer, unique=True)
    event_count: Mapped[int] = mapped_column(Integer)
    merkle_root: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class JobRun(Base):
    """One run of a scheduled job, however it was started (worker, cron or an admin)."""

    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), index=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime())
    finished_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ok: Mapped[bool] = mapped_column(Boolean)
    summary: Mapped[str] = mapped_column(String(500))


def utcnow() -> datetime:
    return datetime.now(UTC)
