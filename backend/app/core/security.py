import base64
import hashlib
import hmac
import time

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException, status

from app.core.config import settings

_password_hasher = PasswordHasher()
_JWT_ALGORITHM = "HS256"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    return _password_hasher.hash(password)


def _verify_pbkdf2(password: str, encoded: str) -> bool:
    try:
        scheme, salt, expected = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), 310_000)
        return hmac.compare_digest(_b64(actual), expected)
    except (ValueError, TypeError):
        return False


def verify_password(password: str, encoded: str) -> bool:
    if encoded.startswith("$argon2id$"):
        try:
            return _password_hasher.verify(encoded, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False
    return _verify_pbkdf2(password, encoded)


def password_needs_rehash(encoded: str) -> bool:
    if not encoded.startswith("$argon2id$"):
        return True
    try:
        return _password_hasher.check_needs_rehash(encoded)
    except InvalidHashError:
        return True


def create_access_token(subject: str, workspace_id: str, role: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": subject,
            "workspace_id": workspace_id,
            "role": role,
            "iat": now,
            "exp": now + settings.access_token_minutes * 60,
        },
        settings.secret_key,
        algorithm=_JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[_JWT_ALGORITHM],
            options={
                "require": ["sub", "workspace_id", "role", "iat", "exp"],
            },
        )
        if not all(
            isinstance(claims.get(name), str) and claims[name]
            for name in ("sub", "workspace_id", "role")
        ):
            raise jwt.InvalidTokenError("Invalid access token claims.")
        return claims
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
