import uuid

from fastapi import APIRouter, Query
from sqlalchemy import select

from ..deps import DB, Admin, CurrentUser, EnvDep
from ..errors import Forbidden, NotFound
from ..lots import current_rate
from ..models import KycStatus, Material, ReferenceRate, Role, User
from ..pricing import GRADES
from ..schemas import (
    CatalogueOut,
    GradeOut,
    KycDecisionIn,
    MaterialOut,
    RateIn,
    SellerOut,
    UserOut,
)

router = APIRouter(tags=["catalogue"])
admin = APIRouter(prefix="/admin", tags=["admin"])


def _material_out(db, env, material: Material) -> MaterialOut:
    rate = current_rate(db, material, env.now())
    return MaterialOut(
        code=material.code,
        name=material.name,
        family=material.family,
        description=material.description,
        reference_rate_paise_per_kg=rate.rate_paise_per_kg if rate else None,
        rate_effective_from=rate.effective_from if rate else None,
    )


@router.get("/materials", response_model=CatalogueOut)
def catalogue(db: DB, env: EnvDep) -> CatalogueOut:
    """Public on purpose: reference prices are the transparency the platform exists to provide."""
    materials = db.scalars(select(Material).order_by(Material.family, Material.name))
    return CatalogueOut(
        materials=[_material_out(db, env, m) for m in materials],
        grades=[
            GradeOut(code=g.code, label=g.label, multiplier=str(g.multiplier))
            for g in GRADES.values()
        ],
    )


@router.get("/sellers/lookup", response_model=SellerOut)
def lookup_seller(
    db: DB, user: CurrentUser, phone: str = Query(pattern=r"^\+?[0-9]{10,15}$")
) -> User:
    """Field agents find the seller they are capturing for by phone number."""
    if user.role not in (Role.AGENT, Role.ADMIN):
        raise Forbidden("only field agents can look up sellers")
    seller = db.scalars(select(User).where(User.phone == phone, User.role == Role.SELLER)).first()
    if seller is None:
        raise NotFound("no seller is registered with that phone number")
    return seller


@admin.get("/users", response_model=list[UserOut])
def users(db: DB, _: Admin, kyc_status: KycStatus | None = None) -> list[User]:
    query = select(User).order_by(User.created_at)
    if kyc_status is not None:
        query = query.where(User.kyc_status == kyc_status)
    return list(db.scalars(query))


@admin.post("/users/{user_id}/kyc", response_model=UserOut)
def decide_kyc(user_id: uuid.UUID, body: KycDecisionIn, db: DB, _: Admin) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("user not found")
    user.kyc_status = KycStatus.APPROVED if body.decision == "approve" else KycStatus.REJECTED
    user.kyc_note = body.note
    db.commit()
    return user


@admin.put("/materials/{code}/rate", response_model=MaterialOut)
def set_rate(code: str, body: RateIn, db: DB, env: EnvDep, actor: Admin) -> MaterialOut:
    material = db.scalars(select(Material).where(Material.code == code)).first()
    if material is None:
        raise NotFound("material not found")
    db.add(
        ReferenceRate(
            material_id=material.id,
            rate_paise_per_kg=body.rate_paise_per_kg,
            effective_from=env.now(),
            set_by_id=actor.id,
        )
    )
    db.commit()
    return _material_out(db, env, material)
