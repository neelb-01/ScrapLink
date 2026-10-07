import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy.orm import Session

from . import custody
from .config import Settings
from .env import Env
from .errors import Conflict
from .models import Certificate, CustodyEvent, Lot, User
from .pricing import GRADES


def verify_url(settings: Settings, certificate_id: uuid.UUID) -> str:
    return f"{settings.public_base_url.rstrip('/')}/certificates/{certificate_id}/verify"


def issue_certificate(db: Session, env: Env, lot: Lot) -> Certificate:
    events = custody.lot_events(db, lot.id)
    check = custody.verify_chain(events)
    if not check.valid:
        raise Conflict(f"custody chain failed verification, certificate withheld: {check.reason}")

    certificate_id = uuid.uuid4()
    issued_at = env.now()
    pdf = render_pdf(
        lot,
        events,
        head_hash=check.head_hash,
        certificate_id=certificate_id,
        verify_link=verify_url(env.settings, certificate_id),
        issued_at=issued_at,
    )
    certificate = Certificate(
        id=certificate_id,
        lot_id=lot.id,
        head_hash=check.head_hash,
        event_count=check.length,
        pdf_key=env.storage.put("certificates", pdf, ".pdf"),
        pdf_sha256=hashlib.sha256(pdf).hexdigest(),
        issued_at=issued_at,
    )
    db.add(certificate)
    db.flush()
    return certificate


@dataclass(frozen=True)
class Verification:
    valid: bool
    reason: str | None


def verify_certificate(db: Session, certificate: Certificate) -> Verification:
    events = custody.lot_events(db, certificate.lot_id)
    check = custody.verify_chain(events)
    if not check.valid:
        return Verification(False, check.reason)
    if len(events) < certificate.event_count:
        return Verification(False, "events covered by this certificate are missing")
    if events[certificate.event_count - 1].hash != certificate.head_hash:
        return Verification(False, "the certified head hash is not in the recorded chain")
    return Verification(True, None)


# --- PDF -------------------------------------------------------------------------------------


def _latin1(text: str) -> str:
    # The built-in PDF fonts are Latin-1 only. Unicode names need an embedded TTF (Phase 2).
    return text.encode("latin-1", "replace").decode("latin-1")


def _rupees(paise: int) -> str:
    return f"INR {paise // 100:,}.{paise % 100:02d}"


def _kg(grams: int) -> str:
    return f"{Decimal(grams) / 1000:,.3f} kg"


def _party(user: User) -> str:
    parts = [user.name]
    if user.business_name:
        parts.append(user.business_name)
    if user.gstin:
        parts.append(f"GSTIN {user.gstin}")
    elif user.pan:
        parts.append(f"PAN {user.pan}")
    return ", ".join(parts)


def render_pdf(
    lot: Lot,
    events: list[CustodyEvent],
    *,
    head_hash: str,
    certificate_id: uuid.UUID,
    verify_link: str,
    issued_at: datetime,
) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()

    def text(value: str, size: float = 10, style: str = "", font: str = "Helvetica", h: float = 6):
        pdf.set_font(font, style, size)
        pdf.multi_cell(0, h, _latin1(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def heading(value: str):
        pdf.ln(3)
        text(value, 12, "B", h=8)

    def row(label: str, value: str):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(52, 6, _latin1(label))
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _latin1(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    text("ScrapLink Chain-of-Custody Certificate", 16, "B", h=9)
    text(f"Certificate {certificate_id}", 9, font="Courier", h=5)
    text(f"Issued {issued_at:%Y-%m-%d %H:%M} UTC  -  Lot {lot.id}", 9, h=5)

    variance = lot.measured_weight_grams - lot.declared_weight_grams
    heading("Material and settlement")
    row("Material", f"{lot.material.name} ({lot.material.code})")
    row("Grade", f"{lot.grade} - {GRADES[lot.grade].label}")
    row("Declared weight", _kg(lot.declared_weight_grams))
    row("Weighbridge weight", _kg(lot.measured_weight_grams))
    row("Variance", f"{'+' if variance >= 0 else '-'}{_kg(abs(variance))}")
    if lot.settled_weight_grams is not None:
        row(
            "Settled weight",
            f"{_kg(lot.settled_weight_grams)} (agreed when a dispute was resolved)",
        )
    row("Winning bid", f"{_rupees(lot.awarded_rate_paise_per_kg)} per kg")
    row("Settled amount", _rupees(lot.settled_amount_paise))

    heading("Parties")
    row("Seller", _party(lot.seller))
    row("Buyer", _party(lot.awarded_buyer))

    heading("Evidence fingerprints (SHA-256)")
    row("Lot photograph", "")
    text(lot.photo_sha256, 8, font="Courier", h=4)
    row("Weighbridge slip", "")
    text(lot.weighbridge_slip_sha256, 8, font="Courier", h=4)

    heading("Custody record")
    for event in events:
        when = event.recorded_at[:19].replace("T", " ")
        text(
            f"{event.seq:>2}  {when}  {event.event_type:<22} {event.hash[:16]}",
            8,
            font="Courier",
            h=4.5,
        )

    heading("Verification")
    row("Chain head", "")
    text(head_hash, 8, font="Courier", h=4)
    row("Verify at", verify_link)

    pdf.ln(4)
    text(
        "Category and grade were confirmed by the seller; an AI suggestion, where one was "
        "confident enough, was offered as a starting point only. Quantity is the weighbridge "
        "reading recorded by the buyer and accepted by the seller, or, where a dispute was "
        "resolved, the weight agreed then. This certificate attests to "
        "the recorded chain of custody above and remains valid only while that chain verifies.",
        8,
        "I",
        h=4,
    )
    return bytes(pdf.output())
