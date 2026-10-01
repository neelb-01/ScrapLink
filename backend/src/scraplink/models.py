"""Persistence model.

Money is integer paise and weight is integer grams throughout, so no arithmetic in the
trade path ever touches a float.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    TypeDecorator,
    UniqueConstraint,
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
    # Field agents capture lots on a seller's behalf (assisted capture).
    AGENT = "agent"
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
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    family: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(500), default="")


class ReferenceRate(Base):
    """Admin-set market reference for a material at grade A. History is kept, never edited."""

    __tablename__ = "reference_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    rate_paise_per_kg: Mapped[int] = mapped_column(BigInteger)
    effective_from: Mapped[datetime] = mapped_column(UTCDateTime())
    set_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


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
    estimate_rate_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    estimate_total_paise: Mapped[int | None] = mapped_column(BigInteger)
    estimate_low_paise: Mapped[int | None] = mapped_column(BigInteger)
    estimate_high_paise: Mapped[int | None] = mapped_column(BigInteger)

    reserve_rate_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    auction_closes_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    awarded_buyer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    awarded_rate_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)

    pickup_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    measured_weight_grams: Mapped[int | None] = mapped_column(BigInteger)
    weighbridge_slip_key: Mapped[str | None] = mapped_column(String(300))
    weighbridge_slip_sha256: Mapped[str | None] = mapped_column(String(64))

    settled_amount_paise: Mapped[int | None] = mapped_column(BigInteger)

    seller: Mapped[User] = relationship(foreign_keys=[seller_id])
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    awarded_buyer: Mapped[User | None] = relationship(foreign_keys=[awarded_buyer_id])
    material: Mapped[Material | None] = relationship()
    certificate: Mapped[Certificate | None] = relationship(back_populates="lot")


class Bid(Base):
    """Sealed bid, expressed per kg so it settles against the weighbridge weight."""

    __tablename__ = "bids"
    __table_args__ = (UniqueConstraint("lot_id", "buyer_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lots.id"), index=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    rate_paise_per_kg: Mapped[int] = mapped_column(BigInteger)
    placed_at: Mapped[datetime] = mapped_column(UTCDateTime())


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


def utcnow() -> datetime:
    return datetime.now(UTC)
