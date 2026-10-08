"""Valuation: reference rate x grade multiplier x weight, with a reference rate that follows
the market (`market_move`, run nightly by repricing.py).

Deliberately simple and explainable: the seller sees exactly why a lot is worth what it is,
and why the reference price is what it is. Learned price prediction can replace either rule
later without changing their callers.
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


def grade_a_equivalent(rate_paise_per_kg: int, grade: str) -> int:
    """What a price paid for a lot of this grade says about the grade A price."""
    return _round(Decimal(rate_paise_per_kg) / GRADES[grade].multiplier)


def median(values: list[int]) -> int:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return _round(Decimal(ordered[middle - 1] + ordered[middle]) / 2)


@dataclass(frozen=True)
class MarketMove:
    median_paise_per_kg: int
    rate_paise_per_kg: int
    # The full move toward the median was larger than max_step allows.
    capped: bool


def market_move(
    current_paise_per_kg: int, grade_a_rates: list[int], *, blend: Decimal, max_step: Decimal
) -> MarketMove:
    """Move `blend` of the way from the current price toward the median of what trades paid,
    but by no more than `max_step` of the current price. The median ignores a single odd
    trade, the blend keeps one busy day from swinging the price, and the cap bounds any run."""
    target = median(grade_a_rates)
    step = (target - current_paise_per_kg) * blend
    limit = current_paise_per_kg * max_step
    capped = abs(step) > limit
    if capped:
        step = limit if step > 0 else -limit
    return MarketMove(
        median_paise_per_kg=target,
        rate_paise_per_kg=_round(current_paise_per_kg + step),
        capped=capped,
    )
