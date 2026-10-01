import base64
import hashlib
import hmac
import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt

# scrypt from the standard library: memory-hard, no native dependency to build on low-end hosts.
_N, _R, _P, _DKLEN = 2**14, 8, 1, 32


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, derived = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    expected = _unb64(derived)
    candidate = hashlib.scrypt(
        password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
    )
    return hmac.compare_digest(candidate, expected)


def create_access_token(user_id: uuid.UUID, role: str, *, secret: str, ttl_seconds: int) -> str:
    # Wall-clock time, not the injectable business clock: token expiry is checked by PyJWT
    # against real time.
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, *, secret: str) -> uuid.UUID:
    payload = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    return uuid.UUID(payload["sub"])
