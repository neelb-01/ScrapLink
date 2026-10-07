from fastapi import APIRouter

from ..deps import DB, CurrentUser
from ..impact import impact_for
from ..schemas import ImpactOut

router = APIRouter(tags=["impact"])


@router.get("/impact", response_model=ImpactOut)
def impact(db: DB, user: CurrentUser) -> ImpactOut:
    """Weight recycled and emissions avoided through settled trades (illustrative factors)."""
    return ImpactOut.model_validate(impact_for(db, user), from_attributes=True)
