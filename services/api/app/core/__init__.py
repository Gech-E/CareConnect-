"""CareConnect Telehealth Platform - Core Configuration.

Manages all application settings via environment variables with
Pydantic Settings for validation and type safety.
"""

import json
from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
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
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:3005", "http://localhost:3006"]
    )
    ENABLE_DEMO_PROVIDERS: bool = False

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://careconnect:password@localhost:5433/careconnect_db"
    DATABASE_POOL_SIZE: int = Field(20, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(10, ge=0, le=100)
    DATABASE_POOL_TIMEOUT: int = Field(30, ge=1, le=120)
    DATABASE_ECHO: bool = False

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6380/0"
    REDIS_MAX_CONNECTIONS: int = Field(50, ge=1)

    # ── Object Storage (S3/MinIO) ────────────────────────────────
    S3_ENDPOINT_URL: str | None = "http://localhost:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "careconnect-documents"
    S3_REGION: str = "us-east-1"
    S3_PRESIGNED_URL_EXPIRY: int = Field(300, ge=30, le=3600)

    # ── OAuth2 / JWT ─────────────────────────────────────────────
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, ge=1, le=60)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, ge=1, le=30)
    JWT_AUDIENCE: str = "careconnect-api"
    OIDC_ISSUER_URL: str = "http://localhost:8005/api/v1/auth"
    OIDC_CLIENT_ID: str = "careconnect-local"
    OIDC_CLIENT_SECRET: str = "local-secret"

    # ── Celery ───────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6380/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6380/2"

    # ── Rate Limiting ────────────────────────────────────────────
    RATE_LIMIT_AUTH_PER_MINUTE: int = Field(10, ge=1)
    RATE_LIMIT_AUTH_ACCOUNT_PER_MINUTE: int = Field(10, ge=1)
    RATE_LIMIT_API_PER_MINUTE: int = Field(120, ge=1)
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = Field(10, ge=1)

    # ── Notifications (mock in local) ────────────────────────────
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_FROM_EMAIL: str = "noreply@careconnect.health"
    SMS_PROVIDER: str = "mock"
    PUSH_PROVIDER: str = "mock"

    # ── Upload Limits ────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = Field(25, ge=1, le=100)
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
            if v.lstrip().startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("S3_ENDPOINT_URL", mode="before")
    @classmethod
    def empty_endpoint_is_default(cls, value: Any) -> Any:
        return value or None

    @model_validator(mode="after")
    def validate_deployment(self) -> Self:
        for origin in self.ALLOWED_ORIGINS:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("ALLOWED_ORIGINS must contain exact HTTP(S) origins")
        if self.ENVIRONMENT in {Environment.STAGING, Environment.PRODUCTION}:
            if self.DEBUG or self.DATABASE_ECHO:
                raise ValueError("Debug and SQL echo must be disabled outside development")
            if self.ENABLE_DEMO_PROVIDERS:
                raise ValueError("Demo providers cannot be enabled in staging or production")
            required_secret_length = 64 if self.JWT_ALGORITHM == "HS512" else 48
            if len(self.JWT_SECRET_KEY.encode()) < required_secret_length or any(
                marker in self.JWT_SECRET_KEY.lower()
                for marker in ("dev-secret", "change-in-production", "replace-with", "changeme")
            ):
                raise ValueError(
                    f"JWT_SECRET_KEY must be an independently generated {required_secret_length}+ byte secret"
                )
            if not self.OIDC_ISSUER_URL.startswith("https://"):
                raise ValueError("OIDC_ISSUER_URL must use HTTPS outside development")
            if any(not origin.startswith("https://") for origin in self.ALLOWED_ORIGINS):
                raise ValueError("ALLOWED_ORIGINS must use HTTPS outside development")
            database = urlsplit(self.DATABASE_URL)
            if database.password in {None, "", "password", "careconnect", "changeme"}:
                raise ValueError("DATABASE_URL must use a non-default database credential")
            if self.S3_ACCESS_KEY_ID == "minioadmin" or self.S3_SECRET_ACCESS_KEY == "minioadmin":
                raise ValueError("Object storage must not use development credentials")
            if self.S3_ENDPOINT_URL and not self.S3_ENDPOINT_URL.startswith("https://"):
                raise ValueError("S3_ENDPOINT_URL must use HTTPS outside development")
        return self

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
