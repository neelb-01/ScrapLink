import uuid

from fastapi import APIRouter
from sqlalchemy import select

from .. import compliance
from ..deps import DB, Admin, EnvDep
from ..errors import NotFound
from ..lots import current_rate
from ..models import KycStatus, Material, RateSource, ReferenceRate, User
from ..pricing import GRADES
from ..schemas import (
    CatalogueOut,
    GradeOut,
    KycDecisionIn,
    MaterialOut,
    PricingRuleOut,
    RateIn,
    RateOut,
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
        rate=RateOut.model_validate(rate) if rate else None,
    )


def _percent(share) -> int:
    return int(share * 100)


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
        pricing_rule=PricingRuleOut(
            window_days=env.settings.reprice_window_days,
            min_trades=env.settings.reprice_min_trades,
            blend_percent=_percent(env.settings.reprice_blend),
            max_step_percent=_percent(env.settings.reprice_max_step),
        ),
    )


@router.get("/materials/{code}/rates", response_model=list[RateOut])
def rate_history(code: str, db: DB, env: EnvDep, limit: int = 30) -> list[ReferenceRate]:
    """Newest first. Public, like the catalogue: how a price got here is part of its case."""
    material = db.scalars(select(Material).where(Material.code == code)).first()
    if material is None:
        raise NotFound("material not found")
    return list(
        db.scalars(
            select(ReferenceRate)
            .where(
                ReferenceRate.material_id == material.id,
                ReferenceRate.effective_from <= env.now(),
            )
            .order_by(ReferenceRate.effective_from.desc(), ReferenceRate.id.desc())
            .limit(min(max(limit, 1), 100))
        )
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
    previous = current_rate(db, material, env.now())
    db.add(
        ReferenceRate(
            material_id=material.id,
            rate_paise_per_kg=body.rate_paise_per_kg,
            effective_from=env.now(),
            set_by_id=actor.id,
            source=RateSource.ADMIN,
            previous_rate_paise_per_kg=previous.rate_paise_per_kg if previous else None,
        )
    )
    db.commit()
    return _material_out(db, env, material)
