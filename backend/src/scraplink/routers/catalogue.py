import uuid

from fastapi import APIRouter
from sqlalchemy import select

from .. import compliance
from ..deps import DB, Admin, EnvDep
from ..errors import NotFound
from ..lots import current_rate
from ..models import KycStatus, Material, ReferenceRate, User
from ..pricing import GRADES
from ..schemas import (
    CatalogueOut,
    GradeOut,
    KycDecisionIn,
    MaterialOut,
    RateIn,
    UserOut,
)
from ..seed import FAMILIES

router = APIRouter(tags=["catalogue"])
admin = APIRouter(prefix="/admin", tags=["admin"])


def _material_out(db, env, material: Material) -> MaterialOut:
    rate = current_rate(db, material, env.now())
    return MaterialOut(
        code=material.code,
        name=material.name,
        family=material.family,
        description=material.description,
        authorisation=material.authorisation,
        reference_rate_paise_per_kg=rate.rate_paise_per_kg if rate else None,
        rate_effective_from=rate.effective_from if rate else None,
    )


@router.get("/materials", response_model=CatalogueOut)
def catalogue(db: DB, env: EnvDep) -> CatalogueOut:
    """Public on purpose: reference prices are the transparency the platform exists to provide."""
    materials = sorted(
        db.scalars(select(Material)),
        key=lambda m: (FAMILIES.index(m.family) if m.family in FAMILIES else len(FAMILIES), m.name),
    )
    return CatalogueOut(
        materials=[_material_out(db, env, m) for m in materials],
        grades=[
            GradeOut(code=g.code, label=g.label, multiplier=str(g.multiplier))
            for g in GRADES.values()
        ],
    )


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
    if body.decision == "approve":
        compliance.set_held(user, body.authorisations)
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
