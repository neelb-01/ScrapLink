"""First-slice catalogue: metal scrap only.

Metals are priced by weight, have public reference prices, and differ visibly between grades,
which makes them the most tractable category for photo-assisted capture.

The seed rates are ILLUSTRATIVE placeholders so a fresh install can run end to end. An admin
must set current market rates (PUT /admin/materials/{code}/rate) before any real trade.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Material, ReferenceRate

# code, name, family, description, illustrative grade-A rate in paise per kg
METALS = [
    (
        "steel_hms",
        "Steel - heavy melting scrap (HMS 1 & 2)",
        "ferrous",
        "Structural steel, plate, beams, pipe offcuts",
        3_200,
    ),
    (
        "cast_iron",
        "Cast iron",
        "ferrous",
        "Engine blocks, machine bases, pipes, manhole covers",
        3_000,
    ),
    (
        "copper",
        "Copper",
        "non_ferrous",
        "Stripped wire and cable, pipe, bus bar",
        68_000,
    ),
    (
        "brass",
        "Brass",
        "non_ferrous",
        "Valves, fittings, taps, radiators",
        45_000,
    ),
    (
        "aluminium",
        "Aluminium",
        "non_ferrous",
        "Extrusions, sheet, castings, utensils",
        16_000,
    ),
]


def seed_materials(db: Session, now: datetime) -> int:
    """Idempotent. Returns how many materials were added."""
    added = 0
    for code, name, family, description, rate in METALS:
        if db.scalars(select(Material).where(Material.code == code)).first():
            continue
        material = Material(code=code, name=name, family=family, description=description)
        db.add(material)
        db.flush()
        db.add(ReferenceRate(material_id=material.id, rate_paise_per_kg=rate, effective_from=now))
        added += 1
    return added
