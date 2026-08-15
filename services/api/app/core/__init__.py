"""CareConnect Telehealth Platform - Core Configuration.

Manages all application settings via environment variables with
Pydantic Settings for validation and type safety.
"""

from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All sensitive values are loaded from environment; no defaults
    for secrets in production.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "CareConnect Telehealth"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.LOCAL
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = Field(default=["http://localhost:3005", "http://localhost:3006"])

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://careconnect:password@localhost:5433/careconnect_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6380/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # ── Object Storage (S3/MinIO) ────────────────────────────────
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "careconnect-documents"
    S3_REGION: str = "us-east-1"
    S3_PRESIGNED_URL_EXPIRY: int = 300  # seconds

    # ── OAuth2 / JWT ─────────────────────────────────────────────
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OIDC_ISSUER_URL: str = "http://localhost:8005/api/v1/auth"
    OIDC_CLIENT_ID: str = "careconnect-local"
    OIDC_CLIENT_SECRET: str = "local-secret"

    # ── Celery ───────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6380/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6380/2"

    # ── Rate Limiting ────────────────────────────────────────────
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_API_PER_MINUTE: int = 120
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 10

    # ── Notifications (mock in local) ────────────────────────────
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_FROM_EMAIL: str = "noreply@careconnect.health"
    SMS_PROVIDER: str = "mock"
    PUSH_PROVIDER: str = "mock"

    # ── Upload Limits ────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_UPLOAD_TYPES: list[str] = Field(
        default=[
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/webp",
        ]
    )

    # ── Appointment ──────────────────────────────────────────────
    SLOT_HOLD_TTL_SECONDS: int = 300
    APPOINTMENT_WINDOW_MINUTES: int = 15
    DEFAULT_VISIT_DURATION_MINUTES: int = 30

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == Environment.LOCAL


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
