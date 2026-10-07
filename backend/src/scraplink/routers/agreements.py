import uuid

from fastapi import APIRouter

from .. import agreements
from ..deps import DB, CurrentUser, EnvDep
from ..models import SupplyAgreement, User
from ..schemas import AgreementIn, AgreementOut, PartyOut

router = APIRouter(prefix="/agreements", tags=["agreements"])


def _party(user: User) -> PartyOut:
    return PartyOut(id=user.id, name=user.name, business_name=user.business_name)


def _out(agreement: SupplyAgreement) -> AgreementOut:
    return AgreementOut(
        id=agreement.id,
        buyer=_party(agreement.buyer),
        seller=_party(agreement.seller),
        material_code=agreement.material.code,
        material_name=agreement.material.name,
        monthly_quantity_grams=agreement.monthly_quantity_grams,
        rate_paise_per_kg=agreement.rate_paise_per_kg,
        starts_on=agreement.starts_on,
        months=agreement.months,
        status=agreement.status,
        created_at=agreement.created_at,
        decided_at=agreement.decided_at,
    )


@router.get("/partners", response_model=list[PartyOut])
def partners(db: DB, user: CurrentUser) -> list[PartyOut]:
    """Sellers the signed-in buyer has bought from: who they can propose an agreement to."""
    return [_party(seller) for seller in agreements.trading_partners(db, user)]


@router.post("", status_code=201, response_model=AgreementOut)
def propose(body: AgreementIn, db: DB, env: EnvDep, user: CurrentUser) -> AgreementOut:
    agreement = agreements.propose(
        db,
        env,
        user,
        seller_id=body.seller_id,
        material_code=body.material_code,
        monthly_quantity_grams=body.monthly_quantity_grams,
        rate_paise_per_kg=body.rate_paise_per_kg,
        starts_on=body.starts_on,
        months=body.months,
    )
    db.commit()
    db.refresh(agreement)
    return _out(agreement)


@router.get("", response_model=list[AgreementOut])
def list_agreements(db: DB, user: CurrentUser) -> list[AgreementOut]:
    return [_out(a) for a in agreements.visible_agreements(db, user)]


@router.post("/{agreement_id}/accept", response_model=AgreementOut)
def accept(agreement_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> AgreementOut:
    agreement = agreements.decide(db, env, user, agreement_id, accept=True)
    db.commit()
    return _out(agreement)


@router.post("/{agreement_id}/decline", response_model=AgreementOut)
def decline(agreement_id: uuid.UUID, db: DB, env: EnvDep, user: CurrentUser) -> AgreementOut:
    agreement = agreements.decide(db, env, user, agreement_id, accept=False)
    db.commit()
    return _out(agreement)
