"""Offline format checks for Indian business identifiers.

These catch typos and fabricated numbers; they do not prove the registration is live.
An admin still approves every account, and a GSTN lookup replaces this in a later phase.
"""

import re

_GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def gstin_check_char(first14: str) -> str:
    total = 0
    for index, char in enumerate(first14):
        product = _GSTIN_CHARS.index(char) * (1 if index % 2 == 0 else 2)
        total += product // 36 + product % 36
    return _GSTIN_CHARS[(36 - total % 36) % 36]


def normalise_gstin(raw: str) -> str:
    gstin = raw.strip().upper()
    if not _GSTIN_RE.match(gstin):
        raise ValueError("GSTIN must be 15 characters: state code, PAN, entity number, Z, check")
    if gstin_check_char(gstin[:14]) != gstin[14]:
        raise ValueError("GSTIN check character does not match; please re-check the number")
    return gstin


def normalise_pan(raw: str) -> str:
    pan = raw.strip().upper()
    if not _PAN_RE.match(pan):
        raise ValueError("PAN must be 10 characters: 5 letters, 4 digits, 1 letter")
    return pan


def pan_in_gstin(gstin: str) -> str:
    return gstin[2:12]
