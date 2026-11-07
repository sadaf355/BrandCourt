import base64
import hashlib
import time

import jwt
import pytest
from fastapi import HTTPException
from app.core.config import Settings
from pydantic import ValidationError
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)


def _legacy_pbkdf2_hash(password: str) -> str:
    salt = b"legacy-test-salt"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    encoded_salt = base64.urlsafe_b64encode(salt).rstrip(b"=").decode()
    encoded_digest = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return f"pbkdf2_sha256${encoded_salt}${encoded_digest}"


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password('safe-password-123')
    second = hash_password('safe-password-123')
    assert first != second
    assert first.startswith("$argon2id$")
    assert verify_password('safe-password-123', first)
    assert not verify_password('wrong-password', first)
    assert not password_needs_rehash(first)


def test_legacy_pbkdf2_password_verifies_and_requires_rehash():
    legacy_hash = _legacy_pbkdf2_hash("safe-password-123")

    assert verify_password("safe-password-123", legacy_hash)
    assert not verify_password("wrong-password", legacy_hash)
    assert password_needs_rehash(legacy_hash)


def test_access_token_contains_workspace_and_role() -> None:
    token = create_access_token('user-1', 'workspace-1', 'admin')
    claims = decode_access_token(token)
    assert claims['sub'] == 'user-1'
    assert claims['workspace_id'] == 'workspace-1'
    assert claims['role'] == 'admin'


def test_access_token_lifetime_is_short():
    token = create_access_token('user-1', 'workspace-1', 'admin')
    claims = decode_access_token(token)
    assert claims['exp'] - claims['iat'] <= 60 * 60


def test_invalid_access_token_is_rejected():
    token = create_access_token("user-1", "workspace-1", "admin")
    header, payload, signature = token.split(".")
    changed_signature = ("a" if signature[0] != "a" else "b") + signature[1:]
    invalid_token = ".".join((header, payload, changed_signature))

    with pytest.raises(HTTPException) as error:
        decode_access_token(invalid_token)

    assert error.value.status_code == 401


def test_expired_access_token_is_rejected():
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user-1",
            "workspace_id": "workspace-1",
            "role": "admin",
            "iat": now - 120,
            "exp": now - 60,
        },
        settings.secret_key,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        decode_access_token(token)

    assert error.value.status_code == 401


@pytest.mark.parametrize("origins", ["*", "https://example.com/path", "javascript://example.com"])
def test_cors_requires_explicit_http_origins(origins):
    with pytest.raises(ValidationError):
        Settings(cors_origins=origins)


def test_production_requires_a_strong_secret():
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="too-short")
