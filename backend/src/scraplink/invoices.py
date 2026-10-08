"""Tax invoices for settled trades.

First slice: settling a trade issues its invoice automatically: a number in one platform-wide
series per financial year (INV/2026-27/0001) and a date, stored. The figures are computed from
the settled lot whenever the invoice is opened, so they always match the trade. Numbering in each
supplier's own GST series, e-invoicing (IRN) and collecting GST through escrow come later.
The HSN codes and the single 18% rate are working values that the finance team must confirm per
material before these invoices are used for tax.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .errors import Conflict
from .models import IssuedInvoice, Lot, LotStatus, User
from .routing import IST

HSN: dict[str, str] = {
    "steel_hms": "7204",
    "cast_iron": "7204",
    "copper": "7404",
    "brass": "7404",
    "aluminium": "7602",
    "pet_bottles": "3915",
    "hdpe": "3915",
    "occ_cardboard": "4707",
    "glass_cullet": "7001",
    "textile_waste": "6310",
    "e_waste_boards": "8549",
    "lead_acid_batteries": "8549",
}
GST_PERCENT = Decimal("18")


@dataclass(frozen=True)
class Party:
    name: str
    gstin: str | None


@dataclass(frozen=True)
class TaxLine:
    label: str
    percent: str
    amount_paise: int


@dataclass(frozen=True)
class Invoice:
    number: str
    issued_at: datetime
    supplier: Party
    recipient: Party
    description: str
    hsn: str | None
    quantity_grams: int
    rate_paise_per_kg: int
    taxable_paise: int
    taxes: list[TaxLine]
    total_paise: int
    # The seller isn't GST-registered, so the registered buyer pays the tax to the government.
    reverse_charge: bool
    # True until the trade's invoice has been issued (lots settled before numbering existed).
    draft: bool = True


def _percent_of(paise: int, percent: Decimal) -> int:
    return int((paise * percent / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _party(user: User) -> Party:
    return Party(name=user.business_name or user.name, gstin=user.gstin)


def draft_invoice(lot: Lot) -> Invoice:
    if lot.status != LotStatus.SETTLED or lot.certificate is None:
        raise Conflict("an invoice is drawn up once the trade has settled")
    seller, buyer = lot.seller, lot.awarded_buyer
    taxable = lot.settled_amount_paise

    if seller.gstin and buyer.gstin and seller.gstin[:2] == buyer.gstin[:2]:
        half = GST_PERCENT / 2
        taxes = [
            TaxLine("CGST", str(half), _percent_of(taxable, half)),
            TaxLine("SGST", str(half), _percent_of(taxable, half)),
        ]
    else:
        # Different states, or the seller's state is unknown because they have no GSTIN.
        taxes = [TaxLine("IGST", str(GST_PERCENT), _percent_of(taxable, GST_PERCENT))]

    return Invoice(
        number=f"DRAFT-{lot.id.hex[:8].upper()}",
        issued_at=lot.certificate.issued_at,
        supplier=_party(seller),
        recipient=_party(buyer),
        description=f"{lot.material.name}, grade {lot.grade}",
        hsn=HSN.get(lot.material.code),
        quantity_grams=lot.billed_weight_grams,
        rate_paise_per_kg=lot.awarded_rate_paise_per_kg,
        taxable_paise=taxable,
        taxes=taxes,
        total_paise=taxable + sum(t.amount_paise for t in taxes),
        reverse_charge=seller.gstin is None,
    )


def financial_year(moment: datetime) -> str:
    """India's financial year runs April to March: 2026-27 for any day from 1 April 2026."""
    day = moment.astimezone(IST).date()
    start = day.year if day.month >= 4 else day.year - 1
    return f"{start}-{str(start + 1)[2:]}"


def issue_invoice(db: Session, lot: Lot, now: datetime) -> IssuedInvoice:
    """Number the settled trade's invoice. Called once, in the settlement's transaction."""
    prefix = f"INV/{financial_year(now)}/"
    issued = db.scalar(
        select(func.count())
        .select_from(IssuedInvoice)
        .where(IssuedInvoice.number.like(f"{prefix}%"))
    )
    record = IssuedInvoice(lot_id=lot.id, number=f"{prefix}{issued + 1:04d}", issued_at=now)
    db.add(record)
    db.flush()
    return record


def invoice_for(db: Session, lot: Lot) -> Invoice:
    invoice = draft_invoice(lot)
    record = db.scalars(select(IssuedInvoice).where(IssuedInvoice.lot_id == lot.id)).first()
    if record is None:
        return invoice
    return replace(invoice, number=record.number, issued_at=record.issued_at, draft=False)
