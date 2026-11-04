import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from server.config import Settings
from server.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

SETTINGS = Settings(_env_file=None, jwt_secret="test-secret-" + "x" * 32)


def test_password_round_trip():
    hashed = hash_password("correct horse battery")
    assert hashed != "correct horse battery"
    assert verify_password("correct horse battery", hashed)
    assert not verify_password("wrong", hashed)


def test_long_passwords_differ_after_72_bytes():
    base = "a" * 80
    hashed = hash_password(base + "1")
    assert not verify_password(base + "2", hashed)


def test_verify_handles_garbage_hash():
    assert verify_password("x", "not-a-bcrypt-hash") is False


def test_token_round_trip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, SETTINGS)
    assert decode_access_token(token, SETTINGS) == user_id


def test_expired_token_rejected():
    past = datetime.now(UTC) - timedelta(hours=2)
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "iat": past, "exp": past + timedelta(hours=1)},
        SETTINGS.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(TokenError):
        decode_access_token(token, SETTINGS)


def test_token_from_other_key_rejected():
    other = Settings(_env_file=None, jwt_secret="another-secret-" + "y" * 32)
    token = create_access_token(uuid.uuid4(), other)
    with pytest.raises(TokenError):
        decode_access_token(token, SETTINGS)


def test_missing_secret_is_a_clear_error():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        create_access_token(uuid.uuid4(), Settings(_env_file=None, jwt_secret=""))
