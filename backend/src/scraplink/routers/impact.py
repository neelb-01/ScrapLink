from fastapi import APIRouter, Response

from ..deps import DB, CurrentUser
from ..impact import impact_csv, impact_for
from ..schemas import ImpactOut

router = APIRouter(tags=["impact"])


@router.get("/impact", response_model=ImpactOut)
def impact(db: DB, user: CurrentUser) -> ImpactOut:
    """Weight recycled and emissions avoided through settled trades (illustrative factors)."""
    return ImpactOut.model_validate(impact_for(db, user), from_attributes=True)


@router.get("/impact.csv")
def impact_download(db: DB, user: CurrentUser) -> Response:
    """The same report as a CSV file. The printable page in the app is the PDF route."""
    return Response(
        impact_csv(impact_for(db, user)),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="scraplink-impact.csv"'},
    )
