import uuid

from fastapi import APIRouter, Response

from .. import lots
from ..certificates import verify_certificate, verify_url
from ..deps import DB, CurrentUser, EnvDep
from ..errors import NotFound
from ..models import Certificate, Role, User
from ..schemas import CertificateOut, VerificationOut

router = APIRouter(prefix="/certificates", tags=["certificates"])


def _certificate_for_party(db, certificate_id: uuid.UUID, user: User) -> Certificate:
    certificate = db.get(Certificate, certificate_id)
    if certificate is None:
        raise NotFound("certificate not found")
    lot = certificate.lot
    if not (
        user.role == Role.ADMIN or lots.is_seller_side(lot, user) or lot.awarded_buyer_id == user.id
    ):
        raise NotFound("certificate not found")
    return certificate


@router.get("/{certificate_id}", response_model=CertificateOut)
def certificate(
    certificate_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser
) -> CertificateOut:
    cert = _certificate_for_party(db, certificate_id, user)
    return CertificateOut(
        id=cert.id,
        lot_id=cert.lot_id,
        head_hash=cert.head_hash,
        event_count=cert.event_count,
        pdf_sha256=cert.pdf_sha256,
        issued_at=cert.issued_at,
        pdf_url=f"/certificates/{cert.id}/pdf",
        verify_url=verify_url(env.settings, cert.id),
    )


@router.get("/{certificate_id}/pdf")
def certificate_pdf(certificate_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> Response:
    cert = _certificate_for_party(db, certificate_id, user)
    return Response(
        env.storage.get(cert.pdf_key),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="scraplink-certificate-{cert.id}.pdf"'},
    )


@router.get("/{certificate_id}/verify", response_model=VerificationOut)
def verify(certificate_id: uuid.UUID, db: DB) -> VerificationOut:
    """Public: anyone holding the certificate (an auditor, a regulator) can check it."""
    cert = db.get(Certificate, certificate_id)
    if cert is None:
        raise NotFound("certificate not found")
    result = verify_certificate(db, cert)
    return VerificationOut(
        certificate_id=cert.id,
        lot_id=cert.lot_id,
        valid=result.valid,
        reason=result.reason,
        head_hash=cert.head_hash,
        event_count=cert.event_count,
        pdf_sha256=cert.pdf_sha256,
    )
