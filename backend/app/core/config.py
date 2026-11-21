"""
Core Application Configuration
India Legal News Aggregator - Free-Tier MVP Architecture
Uses Pydantic BaseSettings for strict environment variable validation.
"""

import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables and .env file.
    Validates configuration strictly using Pydantic v2 BaseSettings.
    """
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project metadata
    PROJECT_NAME: str = Field(
        default="India Legal News Aggregator",
        description="Application name displayed in OpenAPI documentation",
    )
    VERSION: str = Field(
        default="2.0.0",
        description="Application semantic version",
    )
    API_V1_STR: str = Field(
        default="/api/v1",
        description="Base routing prefix for API version 1",
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="Deployment environment ('development', 'staging', 'production')",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')",
    )

    # Database Configuration (PostgreSQL 15+ with pgvector async engine)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/india_legal_aggregator",
        description="Async PostgreSQL connection string with asyncpg driver",
    )

    # Redis Cache Configuration (Upstash / Local Redis)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for response caching and rate limiting",
    )

    # Authentication & Security
    JWT_SECRET: str = Field(
        default="insecure_dev_jwt_secret_key_change_in_production_min_32_characters",
        description="Secret key for signing HS256 JWT tokens",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Cryptographic algorithm for JWT encoding/decoding",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,  # 30 minutes for short-lived access tokens
        description="Validity duration of access tokens in minutes",
    )

    # Third-Party Auth & Integrations
    GOOGLE_CLIENT_ID: str | None = Field(
        default=None,
        description="Google OAuth Client ID for SSO token verification",
    )
    ADMIN_API_KEY: str = Field(
        default="dev-admin-secret-key-change-in-production",
        description="API Key required for administrative operations like manual RSS triggers",
    )
    AUTHORIZED_API_KEYS: list[str] = Field(
        default_factory=list,
        description="List of pre-shared VIP API keys",
    )
    PUBLIC_SEARCH_RATE_LIMIT_PER_MINUTE: int = Field(
        default=30,
        description="Max search requests per minute per IP for anonymous users",
    )
    FEEDBACK_NOTIFICATION_EMAIL: str | None = Field(
        default=None,
        description="Optional recipient email address for newly submitted user reviews",
    )

    # Embeddings & Inference Configuration (< 250 MB RAM constraint)
    EMBEDDING_PROVIDER: str = Field(
        default="onnx",
        description="Embedding generation strategy: 'onnx', 'hf', or 'deterministic'",
    )
    HF_API_TOKEN: str | None = Field(
        default=None,
        description="Optional Hugging Face Inference API token for cloud embeddings",
    )

    # CORS Configuration
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        description="List of allowed CORS origins for frontend communication",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        """
        Ensures postgresql+asyncpg:// driver prefix for PostgreSQL connections,
        automatically converting standard Neon/Supabase postgres:// or postgresql:// schemes.
        """
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("postgres://"):
                return v_stripped.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v_stripped.startswith("postgresql://") and not v_stripped.startswith("postgresql+"):
                return v_stripped.replace("postgresql://", "postgresql+asyncpg://", 1)
            return v_stripped
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """
        Parses CORS origins from either a JSON array string or a comma-separated string.
        """
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                return []
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in v_stripped.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(origin) for origin in v]
        return []

    @field_validator("AUTHORIZED_API_KEYS", mode="before")
    @classmethod
    def assemble_authorized_api_keys(cls, v: Any) -> list[str]:
        """
        Parses authorized VIP API keys from a comma-separated string, JSON array, or list.
        """
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                return []
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    loaded = json.loads(v_stripped)
                    if isinstance(loaded, list):
                        return [str(k).strip() for k in loaded if str(k).strip()]
                except json.JSONDecodeError:
                    pass
            return [k.strip() for k in v_stripped.split(",") if k.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(k).strip() for k in v if str(k).strip()]
        return []


# Global settings singleton instance
settings = Settings()
