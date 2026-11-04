"""Password hashing and access tokens."""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from server.config import Settings, get_settings


class TokenError(Exception):
    """The token is missing, malformed, expired or signed with another key."""


def _prehash(password: str) -> bytes:
    # bcrypt only reads the first 72 bytes (newer versions refuse longer input).
    # Hashing first keeps every character significant for any password length.
    return base64.b64encode(hashlib.sha256(password.encode()).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode())
    except ValueError:
        return False


def _secret(settings: Settings) -> str:
    secret = settings.jwt_secret.get_secret_value()
    if not secret:
        raise RuntimeError("JWT_SECRET is not set; add it to .env")
    return secret


def create_access_token(user_id: uuid.UUID, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(claims, _secret(settings), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> uuid.UUID:
    """User id from a valid access token; raises TokenError otherwise."""
    settings = settings or get_settings()
    try:
        claims = jwt.decode(
            token,
            _secret(settings),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if claims.get("type") != "access":
        raise TokenError("not an access token")
    try:
        return uuid.UUID(claims["sub"])
    except ValueError as exc:
        raise TokenError("bad subject") from exc
