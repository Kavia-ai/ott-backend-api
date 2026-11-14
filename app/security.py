from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import get_settings


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return an Argon2 password hash suitable for storage."""
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its stored hash."""
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: str) -> str:
    """Create a time-limited signed token representing one user."""
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": user_id, "exp": expires_at},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> str:
    """Return the user ID contained in a valid signed token."""
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise jwt.InvalidTokenError("Access token has no user subject.")
    return subject
