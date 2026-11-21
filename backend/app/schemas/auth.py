"""
Authentication Pydantic Schemas & DTOs
India Legal News Aggregator - Free-Tier Architecture (< 250 MB RAM)
Strict Pydantic v2 validation for registration, login, Google SSO, and JWT tokens.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for POST /api/v1/auth/register."""
    email: EmailStr = Field(..., description="Valid user email address")
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password (min 8 characters)")
    full_name: str | None = Field(default=None, max_length=255, description="Full name or designation")


class UserLoginRequest(BaseModel):
    """Payload for POST /api/v1/auth/login."""
    email: EmailStr = Field(..., description="Registered account email")
    password: str = Field(..., description="Account password")


class GoogleAuthRequest(BaseModel):
    """Payload for POST /api/v1/auth/google."""
    id_token: str = Field(..., description="Google OAuth2 ID token from Google Identity Services frontend")


class RefreshTokenRequest(BaseModel):
    """Payload for POST /api/v1/auth/refresh."""
    refresh_token: str = Field(..., description="Valid JWT refresh token")


class UserResponse(BaseModel):
    """Public representation of an authenticated user."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime


class TokenResponse(BaseModel):
    """Authentication response returning JWT tokens and user profile."""
    access_token: str = Field(..., description="JWT Bearer access token")
    refresh_token: str | None = Field(default=None, description="JWT Bearer refresh token")
    token_type: str = Field(default="bearer", description="Token type identifier")
    expires_in: int = Field(..., description="Access token expiration period in seconds")
    user: UserResponse = Field(..., description="Current authenticated user details")
