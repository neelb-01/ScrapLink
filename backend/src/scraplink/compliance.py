"""Authorisation-gated matching.

E-waste and batteries may only go to recyclers that hold the matching authorisation, so the
matching rules refuse a non-compliant buyer outright rather than warning them. An admin records
which authorisations a buyer holds when approving them.

First slice: authorisations are a yes/no per category, with no certificate number, expiry or
issuing board yet.
"""

from .errors import Forbidden, Invalid
from .models import Material, User

AUTHORISATIONS: dict[str, str] = {
    "e_waste": "CPCB e-waste recycler authorisation",
    "battery": "CPCB battery waste recycler authorisation",
}


def held(user: User) -> list[str]:
    return [code for code in (user.authorisations or "").split(",") if code]


def set_held(user: User, codes: list[str]) -> None:
    unknown = set(codes) - AUTHORISATIONS.keys()
    if unknown:
        raise Invalid(f"unknown authorisation '{sorted(unknown)[0]}'")
    user.authorisations = ",".join(sorted(set(codes)))


def require_authorised(user: User, material: Material) -> None:
    needed = material.authorisation
    if needed and needed not in held(user):
        raise Forbidden(f"{material.name} can go only to recyclers with a {AUTHORISATIONS[needed]}")
