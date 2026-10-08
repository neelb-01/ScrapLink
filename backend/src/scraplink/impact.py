"""Environmental impact of settled trades: weight kept in the recycling loop, and the emissions
that recycling it avoided compared with making the same material from virgin inputs.

First slice: one factor per material, applied to the weighbridge weight of settled lots. The
factors are ILLUSTRATIVE round numbers of the right order, not values from a cited life-cycle
study, so the figures are an indication and not an ESG disclosure. Replacing them with sourced,
region-specific factors comes before any report leaves the platform.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Lot, LotStatus, Role, User

# kg CO2e avoided per kg recycled
FACTORS: dict[str, Decimal] = {
    "steel_hms": Decimal("1.5"),
    "cast_iron": Decimal("1.5"),
    "copper": Decimal("3.5"),
    "brass": Decimal("3.0"),
    "aluminium": Decimal("9.0"),
    "pet_bottles": Decimal("1.5"),
    "hdpe": Decimal("1.0"),
    "occ_cardboard": Decimal("0.9"),
    "e_waste_boards": Decimal("1.0"),
    "lead_acid_batteries": Decimal("0.7"),
    "glass_cullet": Decimal("0.3"),
    "textile_waste": Decimal("2.0"),
    "organic_waste": Decimal("0.2"),
}


@dataclass
class MaterialImpact:
    code: str
    name: str
    trades: int
    weight_grams: int
    co2e_avoided_grams: int
    value_paise: int = 0


@dataclass
class Impact:
    trades: int
    weight_grams: int
    co2e_avoided_grams: int
    # A seller's revenue, a buyer's spend, or (for admins) the platform's turnover.
    value_paise: int
    materials: list[MaterialImpact]


def impact_for(db: Session, user: User) -> Impact:
    """Sellers see what they sold, buyers what they bought, admins the whole platform."""
    query = select(Lot).where(Lot.status == LotStatus.SETTLED)
    if user.role == Role.SELLER:
        query = query.where(Lot.seller_id == user.id)
    elif user.role == Role.BUYER:
        query = query.where(Lot.awarded_buyer_id == user.id)

    rows: dict[str, MaterialImpact] = {}
    for lot in db.scalars(query):
        code = lot.material.code
        row = rows.setdefault(code, MaterialImpact(code, lot.material.name, 0, 0, 0))
        row.trades += 1
        row.weight_grams += lot.billed_weight_grams
        avoided = lot.billed_weight_grams * FACTORS.get(code, Decimal(0))
        row.co2e_avoided_grams += int(avoided.quantize(Decimal(1), rounding=ROUND_HALF_UP))
        row.value_paise += lot.settled_amount_paise

    materials = sorted(rows.values(), key=lambda r: r.weight_grams, reverse=True)
    return Impact(
        trades=sum(r.trades for r in materials),
        weight_grams=sum(r.weight_grams for r in materials),
        co2e_avoided_grams=sum(r.co2e_avoided_grams for r in materials),
        value_paise=sum(r.value_paise for r in materials),
        materials=materials,
    )


def _decimal(units: int, scale: int, places: int) -> str:
    whole, part = divmod(units, scale)
    return f"{whole}.{part:0{places}d}"


def impact_csv(impact: Impact) -> str:
    """One row per material and a total, in kg and rupees, for spreadsheets."""
    lines = ["material,trades,weight_kg,co2e_avoided_kg,value_inr"]
    rows = [(m.name, m) for m in impact.materials] + [("Total", impact)]
    for name, row in rows:
        lines.append(
            ",".join(
                [
                    f'"{name}"',
                    str(row.trades),
                    _decimal(row.weight_grams, 1000, 3),
                    _decimal(row.co2e_avoided_grams, 1000, 3),
                    _decimal(row.value_paise, 100, 2),
                ]
            )
        )
    return "\n".join(lines) + "\n"
