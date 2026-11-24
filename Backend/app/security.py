import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt

from app.config import get_settings


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def hash_pin(pin: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 200_000)
    return f"pbkdf2_sha256${salt}${base64.b64encode(digest).decode()}"


def verify_pin(pin: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, encoded = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = base64.b64encode(
            hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 200_000)
        ).decode()
        return hmac.compare_digest(candidate, encoded)
    except (ValueError, AttributeError):
        return False


def create_token(user_id: int, role: str, now: datetime | None = None) -> str:
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
