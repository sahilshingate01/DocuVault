"""Security utilities: Password hashing and JWT token handling."""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import uuid
import bcrypt
import jwt
from app.core.config import settings

# In-memory revocation set for blacklisted tokens (e.g. on logout or refresh)
_REVOKED_TOKENS: set[str] = set()


def revoke_token(jti_or_token: str) -> None:
    """Marks a token or JTI identifier as revoked."""
    _REVOKED_TOKENS.add(jti_or_token)


def is_token_revoked(jti_or_token: str) -> bool:
    """Checks if a token or JTI identifier has been revoked."""
    return jti_or_token in _REVOKED_TOKENS


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a bcrypt-hashed password."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generates a secure salted bcrypt hash of the given password."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def validate_password_complexity(password: str) -> tuple[bool, Optional[str]]:
    """
    Enforces strong password complexity standards:
    - At least 8 characters
    - At least 1 lowercase letter
    - At least 1 uppercase letter
    - At least 1 numerical digit
    - At least 1 special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numerical digit."
    special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?/~`"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*...)."
    return True, None


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JSON Web Token for the user subject."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    jti = str(uuid.uuid4())
    to_encode = {
        "exp": expire,
        "iat": now,
        "sub": str(subject),
        "iss": settings.PROJECT_NAME,
        "type": "access",
        "jti": jti,
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed long-lived refresh token for the user subject."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    jti = str(uuid.uuid4())
    to_encode = {
        "exp": expire,
        "iat": now,
        "sub": str(subject),
        "iss": settings.PROJECT_NAME,
        "type": "refresh",
        "jti": jti,
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        if jti and is_token_revoked(jti):
            return None
        if is_token_revoked(token):
            return None
        return payload
    except jwt.PyJWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT refresh token, verifying token type and revocation."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        jti = payload.get("jti")
        if jti and is_token_revoked(jti):
            return None
        if is_token_revoked(token):
            return None
        return payload
    except jwt.PyJWTError:
        return None
