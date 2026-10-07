import uuid

from fastapi import APIRouter

from .. import rfqs
from ..deps import DB, CurrentUser, EnvDep
from ..errors import NotFound
from ..models import Rfq, Role
from ..schemas import PartyOut, RfqIn, RfqOut

router = APIRouter(prefix="/rfqs", tags=["rfqs"])


def _out(rfq: Rfq) -> RfqOut:
    return RfqOut(
        id=rfq.id,
        buyer=PartyOut(id=rfq.buyer.id, name=rfq.buyer.name, business_name=rfq.buyer.business_name),
        material_code=rfq.material.code,
        material_name=rfq.material.name,
        quantity_grams=rfq.quantity_grams,
        target_rate_paise_per_kg=rfq.target_rate_paise_per_kg,
        needed_by=rfq.needed_by,
        note=rfq.note,
        status=rfq.status,
        created_at=rfq.created_at,
    )


@router.post("", status_code=201, response_model=RfqOut)
def post_rfq(body: RfqIn, db: DB, env: EnvDep, user: CurrentUser) -> RfqOut:
    rfq = rfqs.create_rfq(
        db,
        env,
        user,
        material_code=body.material_code,
        quantity_grams=body.quantity_grams,
        target_rate_paise_per_kg=body.target_rate_paise_per_kg,
        needed_by=body.needed_by,
        note=body.note,
    )
    db.commit()
    return _out(rfq)


@router.get("", response_model=list[RfqOut])
def list_rfqs(db: DB, env: EnvDep, user: CurrentUser) -> list[RfqOut]:
    return [_out(rfq) for rfq in rfqs.visible_rfqs(db, env, user)]


@router.post("/{rfq_id}/close", response_model=RfqOut)
def close_rfq(rfq_id: uuid.UUID, db: DB, user: CurrentUser) -> RfqOut:
    rfq = db.get(Rfq, rfq_id)
    # Other buyers' requests are private to them, so to a buyer they don't exist.
    if rfq is None or (user.role == Role.BUYER and rfq.buyer_id != user.id):
        raise NotFound("request not found")
    rfqs.close_rfq(user, rfq)
    db.commit()
    return _out(rfq)
