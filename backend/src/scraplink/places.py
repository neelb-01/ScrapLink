"""Where lots and businesses are: a fixed list of towns, so a seller picks one instead of typing.

First slice: the Kerala districts the pilot starts in and the neighbouring recycling hubs, each
at its town centre. Exact pickup points are still given when a pickup is booked. A wider list (or
a geocoder) comes with the wider rollout.
"""

from dataclasses import dataclass

from .routing import Point, distance_metres


@dataclass(frozen=True)
class Place:
    code: str
    name: str
    state: str
    latitude: float
    longitude: float

    @property
    def point(self) -> Point:
        return (self.latitude, self.longitude)


PLACES: dict[str, Place] = {
    p.code: p
    for p in (
        Place("kochi", "Kochi", "Kerala", 9.9816, 76.2999),
        Place("alappuzha", "Alappuzha", "Kerala", 9.4981, 76.3388),
        Place("kottayam", "Kottayam", "Kerala", 9.5916, 76.5222),
        Place("thrissur", "Thrissur", "Kerala", 10.5276, 76.2144),
        Place("palakkad", "Palakkad", "Kerala", 10.7867, 76.6548),
        Place("malappuram", "Malappuram", "Kerala", 11.0510, 76.0711),
        Place("kozhikode", "Kozhikode", "Kerala", 11.2588, 75.7804),
        Place("kannur", "Kannur", "Kerala", 11.8745, 75.3704),
        Place("kollam", "Kollam", "Kerala", 8.8932, 76.6141),
        Place("thiruvananthapuram", "Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
        Place("coimbatore", "Coimbatore", "Tamil Nadu", 11.0168, 76.9558),
        Place("chennai", "Chennai", "Tamil Nadu", 13.0827, 80.2707),
        Place("mangaluru", "Mangaluru", "Karnataka", 12.9141, 74.8560),
        Place("bengaluru", "Bengaluru", "Karnataka", 12.9716, 77.5946),
    )
}


def km_from(place: Place, point: Point) -> int:
    """Straight-line distance, rounded to whole kilometres."""
    return round(distance_metres(place.point, point) / 1000)
