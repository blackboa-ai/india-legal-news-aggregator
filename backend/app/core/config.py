"""
Core Application Configuration
India Legal News Aggregator - Free-Tier MVP Architecture
Uses Pydantic BaseSettings for strict environment variable validation.
"""

import json

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
        default=60 * 24 * 7,  # 7 days
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


# Global settings singleton instance
settings = Settings()
