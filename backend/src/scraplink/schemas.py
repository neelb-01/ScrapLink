"""API shapes. Money is integer paise and weight integer grams; clients format for display."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class RegisterIn(BaseModel):
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    role: Literal["seller", "buyer"]
    business_name: str | None = Field(default=None, max_length=200)
    gstin: str | None = None
    pan: str | None = None


class LoginIn(BaseModel):
    phone: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str
    name: str
    role: str
    business_name: str | None
    gstin: str | None
    pan: str | None
    kyc_status: str
    kyc_note: str | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class KycDecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)


class RateIn(BaseModel):
    rate_paise_per_kg: int = Field(gt=0)


class GradeOut(BaseModel):
    code: str
    label: str
    multiplier: str


class MaterialOut(BaseModel):
    code: str
    name: str
    family: str
    description: str
    reference_rate_paise_per_kg: int | None
    rate_effective_from: datetime | None


class CatalogueOut(BaseModel):
    materials: list[MaterialOut]
    grades: list[GradeOut]


class ConfirmIn(BaseModel):
    material_code: str
    grade: Literal["A", "B", "C"]
    declared_weight_grams: int = Field(gt=0, le=100_000_000)


class ListIn(BaseModel):
    auction_hours: int = Field(default=24, ge=1, le=168)
    reserve_rate_paise_per_kg: int | None = Field(default=None, gt=0)


class BidIn(BaseModel):
    rate_paise_per_kg: int = Field(gt=0)


class PickupIn(BaseModel):
    pickup_at: AwareDatetime


class DisputeIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class PartyOut(BaseModel):
    id: uuid.UUID
    name: str
    business_name: str | None


class ClassificationOut(BaseModel):
    suggested_material_code: str | None
    suggested_grade: str | None
    confidence: float | None
    # True only when the suggestion cleared the confidence threshold and should be prefilled.
    prefilled: bool
    threshold: float


class EstimateOut(BaseModel):
    reference_rate_paise_per_kg: int
    rate_paise_per_kg: int
    total_paise: int
    low_paise: int
    high_paise: int


class AwardOut(BaseModel):
    buyer: PartyOut
    rate_paise_per_kg: int
    escrow_required_paise: int


class LotOut(BaseModel):
    id: uuid.UUID
    status: str
    created_at: datetime
    seller: PartyOut
    photo_url: str
    photo_sha256: str
    classification: ClassificationOut
    material_code: str | None
    material_name: str | None
    grade: str | None
    declared_weight_grams: int | None
    estimate: EstimateOut | None
    reserve_rate_paise_per_kg: int | None
    auction_closes_at: datetime | None
    bid_count: int
    my_bid_rate_paise_per_kg: int | None
    award: AwardOut | None
    pickup_at: datetime | None
    measured_weight_grams: int | None
    settled_amount_paise: int | None
    certificate_id: uuid.UUID | None


class EscrowOut(BaseModel):
    intent_id: uuid.UUID
    gateway: str
    gateway_order_id: str
    amount_paise: int
    status: str
    # Present for Razorpay so the client can open Checkout against the order.
    razorpay_key_id: str | None = None


class CustodyEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    event_type: str
    payload: dict
    actor_id: uuid.UUID | None
    recorded_at: str
    prev_hash: str
    hash: str


class CertificateOut(BaseModel):
    id: uuid.UUID
    lot_id: uuid.UUID
    head_hash: str
    event_count: int
    pdf_sha256: str
    issued_at: datetime
    pdf_url: str
    verify_url: str


class VerificationOut(BaseModel):
    certificate_id: uuid.UUID
    lot_id: uuid.UUID
    valid: bool
    reason: str | None
    head_hash: str
    event_count: int
    pdf_sha256: str


class WalletEntryOut(BaseModel):
    kind: str
    lot_id: uuid.UUID | None
    amount_paise: int
    created_at: datetime


class WalletOut(BaseModel):
    balance_paise: int
    entries: list[WalletEntryOut]
