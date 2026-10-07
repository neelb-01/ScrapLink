"""Pickup route planning.

First slice: one truck, one day. The day's pickups are put in nearest-next order from the depot
using straight-line distance. That is a quick, explainable heuristic, not an optimal tour: road
distances, time windows, vehicle capacity and several trucks come with the full optimiser.
"""

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Lot, LotStatus

# Pickup days are Indian calendar days. India has one time zone and no daylight saving, so a
# fixed offset is exact and needs no time-zone database (Windows ships without one).
IST = timezone(timedelta(hours=5, minutes=30))
EARTH_RADIUS_METRES = 6_371_000

Point = tuple[float, float]


def distance_metres(a: Point, b: Point) -> int:
    """Great-circle (haversine) distance."""
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return round(2 * EARTH_RADIUS_METRES * math.asin(math.sqrt(h)))


@dataclass
class Stop:
    lot: Lot
    leg_metres: int


@dataclass
class Route:
    day: date
    depot: Point
    stops: list[Stop]
    # Booked for the day without a location, so they can't be placed on the route.
    unplaced: list[Lot]
    return_metres: int

    @property
    def total_metres(self) -> int:
        return sum(s.leg_metres for s in self.stops) + self.return_metres


def nearest_next(depot: Point, points: list[Point]) -> list[int]:
    """Indices of `points` in visiting order: always go to the closest one not yet visited."""
    remaining = list(range(len(points)))
    order: list[int] = []
    here = depot
    while remaining:
        best = min(remaining, key=lambda i: (distance_metres(here, points[i]), i))
        order.append(best)
        remaining.remove(best)
        here = points[best]
    return order


def plan_day(db: Session, day: date, depot: Point) -> Route:
    start = datetime.combine(day, time(0), tzinfo=IST)
    booked = list(
        db.scalars(
            select(Lot)
            .where(
                Lot.status == LotStatus.PICKUP_SCHEDULED,
                Lot.pickup_at >= start,
                Lot.pickup_at < start + timedelta(days=1),
            )
            .order_by(Lot.pickup_at)
        )
    )
    located = [lot for lot in booked if lot.pickup_latitude is not None]
    points = [(lot.pickup_latitude, lot.pickup_longitude) for lot in located]

    stops: list[Stop] = []
    here = depot
    for index in nearest_next(depot, points):
        stops.append(Stop(located[index], distance_metres(here, points[index])))
        here = points[index]
    return Route(
        day=day,
        depot=depot,
        stops=stops,
        unplaced=[lot for lot in booked if lot.pickup_latitude is None],
        return_metres=distance_metres(here, depot) if stops else 0,
    )
