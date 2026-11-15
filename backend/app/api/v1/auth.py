"""
Authentication API Router
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Provides:
- POST /auth/register (Email + password registration)
- POST /auth/login (JWT credential authentication)
- POST /auth/google (Google OAuth2 ID token SSO verification)
- GET /auth/me (Current user profile)
- POST /auth/refresh (JWT token refresh)
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    GoogleAuthRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

logger = logging.getLogger("app.api.v1.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ------------------------------------------------------------------------------
# Google OAuth ID Token Verification (Mockable for tests)
# ------------------------------------------------------------------------------
async def verify_google_id_token(id_token: str, client_id: str | None = None) -> dict[str, Any]:
    """
    Verifies a Google OAuth ID token.
    Can be mocked or monkeypatched during testing.
    In production, validates against Google's tokeninfo endpoint.
    """
    if not id_token or not id_token.strip():
        raise ValueError("Missing or empty Google ID token")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
            )
            if resp.status_code != 200:
                raise ValueError(f"Google token verification failed with status {resp.status_code}")
            data = resp.json()
            if "error" in data or "error_description" in data:
                raise ValueError(data.get("error_description", "Invalid Google ID token"))
            if client_id and data.get("aud") != client_id:
                raise ValueError("Token audience does not match configured GOOGLE_CLIENT_ID")
            return data
        except Exception as exc:
            raise ValueError(f"Failed to verify Google token: {exc}") from exc


# ------------------------------------------------------------------------------
# 1. Register with Email and Password
# ------------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account with email and password",
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new user account.
    Validates uniqueness of email address and returns JWT access & refresh tokens.
    """
    email_clean = payload.email.strip().lower()

    # Check for duplicate email
    stmt = select(User).where(User.email == email_clean)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # Hash password securely
    hashed_pw = get_password_hash(payload.password)
    now = datetime.now(UTC)
    user = User(
        id=uuid.uuid4(),
        email=email_clean,
        hashed_password=hashed_pw,
        full_name=payload.full_name,
        is_active=True,
        is_superuser=False,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


# ------------------------------------------------------------------------------
# 2. Login with Email and Password
# ------------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue JWT access and refresh tokens",
)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies user credentials and issues a fresh JWT Bearer token pair.
    """
    email_clean = payload.email.strip().lower()
    stmt = select(User).where(User.email == email_clean)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


# ------------------------------------------------------------------------------
# 3. Google OAuth ID Token Authentication
# ------------------------------------------------------------------------------
@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Authenticate or register user using Google OAuth ID token",
)
async def login_with_google(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies a Google OAuth ID token, provisions user if new, and issues JWT tokens.
    """
    try:
        google_data = await verify_google_id_token(
            payload.id_token,
            client_id=settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth verification failed: {exc}",
        )

    google_sub = google_data.get("sub")
    email = google_data.get("email")
    full_name = google_data.get("name")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token missing email address",
        )

    email_clean = email.strip().lower()

    # Find user by google_id or email
    stmt = select(User).where((User.google_id == google_sub) | (User.email == email_clean))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if user:
        if not user.google_id and google_sub:
            user.google_id = google_sub
        if full_name and not user.full_name:
            user.full_name = full_name
        await db.commit()
        await db.refresh(user)
    else:
        now = datetime.now(UTC)
        user = User(
            id=uuid.uuid4(),
            email=email_clean,
            google_id=google_sub,
            full_name=full_name,
            hashed_password=None,
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


# ------------------------------------------------------------------------------
# 4. Get Current User Profile
# ------------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get profile of currently authenticated user",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the authenticated user's profile details.
    """
    return UserResponse.model_validate(current_user)


# ------------------------------------------------------------------------------
# 5. Refresh Access Token
# ------------------------------------------------------------------------------
@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange valid refresh token for a new access token",
)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validates refresh token and issues a new access token without re-authenticating.
    """
    claims = decode_token(payload.refresh_token)
    if claims.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type, expected refresh token",
        )

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token claims",
        )

    try:
        uid = uuid.UUID(user_id)
        stmt = select(User).where(User.id == uid)
    except (ValueError, TypeError):
        stmt = select(User).where(User.email == user_id)

    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access_token = create_access_token(subject=str(user.id))

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=payload.refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )
