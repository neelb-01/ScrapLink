"""Starter catalogue.

Metals came first: they are priced by weight, have public reference prices, and differ visibly
between grades, which makes them the most tractable category for photo-assisted capture.
Plastics, paper, e-waste and batteries follow so the catalogue covers the waste streams the
platform targets; the photo suggestion still knows only metals, so sellers choose these by hand.

The seed rates are ILLUSTRATIVE placeholders so a fresh install can run end to end. An admin
must set current market rates (PUT /admin/materials/{code}/rate) before any real trade.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Material, RateSource, ReferenceRate

# code, name, family, description, illustrative grade-A rate in paise per kg, authorisation
MATERIALS = [
    (
        "steel_hms",
        "Steel - heavy melting scrap (HMS 1 & 2)",
        "ferrous",
        "Structural steel, plate, beams, pipe offcuts",
        3_200,
        None,
    ),
    (
        "cast_iron",
        "Cast iron",
        "ferrous",
        "Engine blocks, machine bases, pipes, manhole covers",
        3_000,
        None,
    ),
    (
        "copper",
        "Copper",
        "non_ferrous",
        "Stripped wire and cable, pipe, bus bar",
        68_000,
        None,
    ),
    (
        "brass",
        "Brass",
        "non_ferrous",
        "Valves, fittings, taps, radiators",
        45_000,
        None,
    ),
    (
        "aluminium",
        "Aluminium",
        "non_ferrous",
        "Extrusions, sheet, castings, utensils",
        16_000,
        None,
    ),
    (
        "pet_bottles",
        "PET bottles",
        "plastic",
        "Clear and coloured drink bottles, loose or baled",
        2_800,
        None,
    ),
    (
        "hdpe",
        "HDPE containers",
        "plastic",
        "Cans, drums, crates and pipe",
        3_000,
        None,
    ),
    (
        "occ_cardboard",
        "Cardboard (OCC)",
        "paper",
        "Old corrugated boxes and cartons",
        1_400,
        None,
    ),
    (
        "glass_cullet",
        "Glass bottles and cullet",
        "glass",
        "Clear and coloured bottles, jars and broken glass",
        300,
        None,
    ),
    (
        "textile_waste",
        "Textile waste",
        "textile",
        "Cotton and polyester cuttings, old garments",
        1_200,
        None,
    ),
    (
        "organic_waste",
        "Organic waste",
        "organic",
        "Food, market and garden waste for compost or biogas",
        150,
        None,
    ),
    (
        "e_waste_boards",
        "Circuit boards (e-waste)",
        "e_waste",
        "Computer, telecom and appliance boards",
        15_000,
        "e_waste",
    ),
    (
        "lead_acid_batteries",
        "Lead-acid batteries",
        "battery",
        "Used vehicle and inverter batteries",
        9_000,
        "battery",
    ),
]

# The order families are shown in: metals first, regulated waste last.
FAMILIES = [
    "ferrous",
    "non_ferrous",
    "plastic",
    "paper",
    "glass",
    "textile",
    "organic",
    "e_waste",
    "battery",
]


def seed_materials(db: Session, now: datetime) -> int:
    """Idempotent. Returns how many materials were added."""
    added = 0
    for code, name, family, description, rate, authorisation in MATERIALS:
        if db.scalars(select(Material).where(Material.code == code)).first():
            continue
        material = Material(
            code=code,
            name=name,
            family=family,
            description=description,
            authorisation=authorisation,
        )
        db.add(material)
        db.flush()
        db.add(
            ReferenceRate(
                material_id=material.id,
                rate_paise_per_kg=rate,
                effective_from=now,
                source=RateSource.SEED,
            )
        )
        added += 1
    return added
