from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "baoday"
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


@lru_cache
def dummy_password_hash() -> str:
    # Perform the same password verification when the email does not exist.
    return hash_password("baoday-unused-password-placeholder")


def issue_access_token(user_id: int) -> tuple[str, int]:
    settings = get_settings()
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iss": JWT_ISSUER, "iat": now, "exp": now + lifetime}
    token = jwt.encode(
        payload, settings.jwt_secret_key.get_secret_value(), algorithm=JWT_ALGORITHM
    )
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> int:
    payload = jwt.decode(
        token,
        get_settings().jwt_secret_key.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        options={"require": ["exp", "iat", "iss", "sub"]},
    )
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise jwt.InvalidTokenError("Invalid user ID") from exc
    if not 0 < user_id <= 2**63 - 1:
        raise jwt.InvalidTokenError("Invalid user ID")
    return user_id
