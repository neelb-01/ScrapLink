"""Rules-based valuation: reference rate x grade multiplier x weight.

Deliberately simple and explainable — the seller sees exactly why a lot is worth what it is.
Learned price prediction replaces `estimate` later without changing its callers.
"""

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Grade:
    code: str
    label: str
    multiplier: Decimal


GRADES: dict[str, Grade] = {
    "A": Grade("A", "Clean and sorted: nothing attached, coated or mixed in", Decimal("1.00")),
    "B": Grade("B", "Minor contamination: paint, oil, small attachments", Decimal("0.85")),
    "C": Grade("C", "Mixed or heavily contaminated", Decimal("0.65")),
}


@dataclass(frozen=True)
class Estimate:
    rate_paise_per_kg: int
    total_paise: int
    low_paise: int
    high_paise: int


def _round(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def amount_for(rate_paise_per_kg: int, weight_grams: int) -> int:
    return _round(Decimal(rate_paise_per_kg) * weight_grams / 1000)


def estimate(
    reference_rate_paise_per_kg: int, grade: str, weight_grams: int, band: Decimal
) -> Estimate:
    rate = _round(reference_rate_paise_per_kg * GRADES[grade].multiplier)
    total = amount_for(rate, weight_grams)
    return Estimate(
        rate_paise_per_kg=rate,
        total_paise=total,
        low_paise=_round(total * (1 - band)),
        high_paise=_round(total * (1 + band)),
    )


def escrow_amount(rate_paise_per_kg: int, declared_weight_grams: int, tolerance: Decimal) -> int:
    """What the winning buyer funds: enough to settle a weighbridge reading up to tolerance over."""
    raw = Decimal(rate_paise_per_kg) * declared_weight_grams / 1000 * (1 + tolerance)
    return int(raw.quantize(Decimal(1), rounding=ROUND_CEILING))
