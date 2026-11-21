"""
Core Security & Authentication Module
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Handles password hashing (bcrypt), JWT token generation & verification (python-jose),
and FastAPI authentication dependencies (get_current_user, get_optional_user).
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger("app.core.security")

# ------------------------------------------------------------------------------
# Passlib & Bcrypt Compatibility Layer (Python 3.12+, bcrypt 4.0.0+ / 5.0.0+)
# ------------------------------------------------------------------------------
if not hasattr(bcrypt, "__about__"):
    class _BcryptAbout:
        __version__ = getattr(bcrypt, "__version__", "4.0.1")
    bcrypt.__about__ = _BcryptAbout()

_orig_hashpw = bcrypt.hashpw


def _safe_hashpw(password: bytes | str, salt: bytes) -> bytes:
    """Ensures bcrypt passwords never exceed 72 bytes to prevent library exceptions."""
    if isinstance(password, str):
        password = password.encode("utf-8")
    if len(password) > 72:
        password = password[:72]
    return _orig_hashpw(password, salt)


bcrypt.hashpw = _safe_hashpw

# ------------------------------------------------------------------------------
# Password Hashing Context
# ------------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a stored bcrypt hash.
    Safely truncates to 72 bytes to match bcrypt max input specification.
    """
    if not plain_password or not hashed_password:
        return False
    pw_bytes = plain_password.encode("utf-8") if isinstance(plain_password, str) else plain_password
    pw_bytes = pw_bytes[:72]
    return pwd_context.verify(pw_bytes, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generates a secure salted bcrypt hash for the provided password.
    """
    pw_bytes = password.encode("utf-8") if isinstance(password, str) else password
    pw_bytes = pw_bytes[:72]
    return pwd_context.hash(pw_bytes)


# ------------------------------------------------------------------------------
# JWT Token Generation & Verification
# ------------------------------------------------------------------------------
ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
# Reduced refresh token lifetime to 7 days.
# Note: Refresh token rotation and revocation on use should be implemented for production.
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    claims: dict[str, Any] | None = None,
) -> str:
    """
    Creates a signed HS256 JWT access token.
    Default validity is configured in settings (default 7 days).
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }
    if claims:
        to_encode.update(claims)

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    claims: dict[str, Any] | None = None,
) -> str:
    """
    Creates a signed HS256 JWT refresh token.
    Default validity is 30 days.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
    }
    if claims:
        to_encode.update(claims)

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decodes and cryptographically verifies a JWT token.
    Raises HTTPException 401 if expired or signature is invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ------------------------------------------------------------------------------
# FastAPI Authentication Dependencies
# ------------------------------------------------------------------------------
async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency requiring a valid JWT Bearer access token.
    Resolves the associated User record from the database.
    Raises HTTP 401 if missing, invalid, or expired.
    Raises HTTP 400 if user account is disabled.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    user_id: str | None = payload.get("sub")
    token_type: str | None = payload.get("type")

    if not user_id or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Lookup user by UUID or email
    try:
        uid = uuid.UUID(user_id)
        stmt = select(User).where(User.id == uid)
    except (ValueError, TypeError):
        stmt = select(User).where(User.email == user_id)

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    return user


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    FastAPI dependency that extracts authenticated User if token is present and valid.
    Returns None without throwing 401 if token is absent, invalid, or expired.
    Useful for endpoints supporting both anonymous browsing and personalized features.
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if not user_id or token_type != "access":
            return None

        try:
            uid = uuid.UUID(user_id)
            stmt = select(User).where(User.id == uid)
        except (ValueError, TypeError):
            stmt = select(User).where(User.email == user_id)

        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user and user.is_active:
            return user
        return None
    except Exception:
        return None


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensures authenticated user has superuser privileges.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user
