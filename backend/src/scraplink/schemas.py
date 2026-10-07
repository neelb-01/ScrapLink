"""API shapes. Money is integer paise and weight integer grams; clients format for display."""

import uuid
from datetime import date, datetime
from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

Authorisation = Literal["e_waste", "battery"]


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
    authorisations: list[str]

    @field_validator("authorisations", mode="before")
    @classmethod
    def _split(cls, value):
        return [code for code in value.split(",") if code] if isinstance(value, str) else value


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class KycDecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)
    # Recorded on approval; buyers need them to trade e-waste or batteries.
    authorisations: list[Authorisation] = []


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
    # Only buyers holding this authorisation can bid on or request the material.
    authorisation: str | None
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
    # Optional: where to collect from, used to plan the day's route.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _both_or_neither(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("give both latitude and longitude, or neither")
        return self


class LocationOut(BaseModel):
    latitude: float
    longitude: float


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
    # Set while the lot waits for this buyer to pay; the award lapses after it.
    escrow_due_at: datetime | None


class DisputeInfoOut(BaseModel):
    # "seller": the seller rejected the weighbridge reading. "escrow": the reading cost more than
    # the buyer paid in, so settlement stopped on its own.
    raised_by: Literal["seller", "escrow"]
    reason: str
    raised_at: str


class ResolveIn(BaseModel):
    outcome: Literal["settle", "cancel"]
    note: str = Field(min_length=3, max_length=500)
    # Required to settle: the weight the seller is paid for.
    weight_grams: int | None = Field(default=None, gt=0, le=100_000_000)


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
    material_authorisation: str | None
    grade: str | None
    declared_weight_grams: int | None
    estimate: EstimateOut | None
    reserve_rate_paise_per_kg: int | None
    auction_closes_at: datetime | None
    bid_count: int
    my_bid_rate_paise_per_kg: int | None
    # True when this buyer's bid won but they didn't pay in time or declined.
    my_bid_lapsed: bool
    award: AwardOut | None
    pickup_at: datetime | None
    # Parties only: it is the seller's yard.
    pickup_location: LocationOut | None
    measured_weight_grams: int | None
    # Set when a dispute settled at a weight other than the weighbridge reading.
    settled_weight_grams: int | None
    settled_amount_paise: int | None
    certificate_id: uuid.UUID | None
    # Parties only, while the lot is disputed.
    dispute: DisputeInfoOut | None


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


# --- Requests for quotation --------------------------------------------------------------


class RfqIn(BaseModel):
    material_code: str
    quantity_grams: int = Field(gt=0, le=100_000_000)
    target_rate_paise_per_kg: int | None = Field(default=None, gt=0)
    needed_by: AwareDatetime
    note: str = Field(default="", max_length=500)


class RfqOut(BaseModel):
    id: uuid.UUID
    buyer: PartyOut
    material_code: str
    material_name: str
    quantity_grams: int
    target_rate_paise_per_kg: int | None
    needed_by: datetime
    note: str
    status: str
    created_at: datetime


# --- Supply agreements -------------------------------------------------------------------


class AgreementIn(BaseModel):
    seller_id: uuid.UUID
    material_code: str
    monthly_quantity_grams: int = Field(gt=0, le=100_000_000)
    rate_paise_per_kg: int = Field(gt=0)
    starts_on: date
    months: int = Field(ge=1, le=24)


class AgreementOut(BaseModel):
    id: uuid.UUID
    buyer: PartyOut
    seller: PartyOut
    material_code: str
    material_name: str
    monthly_quantity_grams: int
    rate_paise_per_kg: int
    starts_on: date
    months: int
    status: str
    created_at: datetime
    decided_at: datetime | None


# --- Invoices ----------------------------------------------------------------------------


class InvoicePartyOut(BaseModel):
    name: str
    gstin: str | None


class TaxLineOut(BaseModel):
    label: str
    percent: str
    amount_paise: int


class InvoiceOut(BaseModel):
    number: str
    draft: bool = True
    issued_at: datetime
    supplier: InvoicePartyOut
    recipient: InvoicePartyOut
    description: str
    hsn: str | None
    quantity_grams: int
    rate_paise_per_kg: int
    taxable_paise: int
    taxes: list[TaxLineOut]
    total_paise: int
    reverse_charge: bool


# --- Environmental impact ----------------------------------------------------------------


class MaterialImpactOut(BaseModel):
    code: str
    name: str
    trades: int
    weight_grams: int
    co2e_avoided_grams: int


class ImpactOut(BaseModel):
    trades: int
    weight_grams: int
    co2e_avoided_grams: int
    materials: list[MaterialImpactOut]


# --- Operations (admin) ------------------------------------------------------------------


class TransporterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    vehicle: str = Field(min_length=1, max_length=120)
    capacity_grams: int = Field(gt=0, le=100_000_000)


class TransporterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    vehicle: str
    capacity_grams: int
    created_at: datetime


class RouteStopOut(BaseModel):
    lot_id: uuid.UUID
    seller: PartyOut
    material_name: str | None
    pickup_at: datetime
    location: LocationOut | None
    # Straight-line distance from the previous stop (or the depot); null if unplaced.
    leg_metres: int | None


class RouteOut(BaseModel):
    day: date
    depot: LocationOut
    stops: list[RouteStopOut]
    unplaced: list[RouteStopOut]
    return_metres: int
    total_metres: int


class AnchorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_event_id: int
    last_event_id: int
    event_count: int
    merkle_root: str
    created_at: datetime


class AnchorCheckOut(BaseModel):
    id: int
    holds: bool


class JobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    started_at: datetime
    finished_at: datetime
    ok: bool
    summary: str


class JobOut(BaseModel):
    name: str
    schedule: str
    description: str
    last_run: JobRunOut | None


class DisputeOut(BaseModel):
    lot_id: uuid.UUID
    material_name: str
    seller: PartyOut
    buyer: PartyOut
    dispute: DisputeInfoOut
    rate_paise_per_kg: int
    declared_weight_grams: int
    measured_weight_grams: int
    escrow_held_paise: int
    # The heaviest weight the escrow pays for in full; settling above it is refused.
    max_settle_weight_grams: int
