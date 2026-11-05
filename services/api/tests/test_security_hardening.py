"""Regression coverage for authentication and deployment security boundaries."""

import importlib
import logging
import pkgutil
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import bcrypt
import jwt
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core import Environment, Settings, security
from app.core.exceptions import AppError
from app.core.logging import ExceptionPrivacyFilter, redact_sensitive_fields
from app.schemas.auth import LoginRequest, RegisterRequest


@pytest.fixture(autouse=True)
def load_models():
    import app.models

    for module in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{module.name}")


@pytest.mark.parametrize(
    "origins", ["https://a.example,https://b.example", '["https://a.example", "https://b.example"]']
)
def test_origins_support_documented_environment_formats(monkeypatch, origins):
    monkeypatch.setenv("ALLOWED_ORIGINS", origins)
    assert Settings(_env_file=None).ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]


def production_settings(**changes):
    values = {
        "ENVIRONMENT": "production",
        "JWT_SECRET_KEY": "synthetic-test-secret-" * 4,
        "DATABASE_URL": "postgresql+asyncpg://user:synthetic-secret@db/careconnect",
        "S3_ACCESS_KEY_ID": "synthetic-key",
        "S3_SECRET_ACCESS_KEY": "synthetic-storage-secret",
        "S3_ENDPOINT_URL": "https://storage.example",
        "OIDC_ISSUER_URL": "https://api.example/auth",
        "ALLOWED_ORIGINS": ["https://care.example"],
    }
    return Settings(_env_file=None, **(values | changes))


def test_production_rejects_defaults_and_accepts_explicit_secure_config():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENVIRONMENT="production")
    assert production_settings().is_production


@pytest.mark.parametrize(
    "changes",
    [
        {"DEBUG": True},
        {"DATABASE_ECHO": True},
        {"ENABLE_DEMO_PROVIDERS": True},
        {"ALLOWED_ORIGINS": ["*"]},
        {"ALLOWED_ORIGINS": ["http://care.example"]},
        {"JWT_SECRET_KEY": "short"},
        {"S3_SECRET_ACCESS_KEY": "minioadmin"},
    ],
)
def test_production_rejects_unsafe_configuration(changes):
    with pytest.raises(ValidationError):
        production_settings(**changes)


def test_passwords_preserve_whitespace_and_unicode_beyond_bcrypt_limit():
    password = " " + "🙂" * 30 + "tail "
    assert RegisterRequest(email="test@example.com", password=password).password == password
    assert LoginRequest(email="test@example.com", password=password).password == password
    hashed = security.hash_password(password)
    assert hashed.startswith("$argon2id$")
    assert security.verify_password(password, hashed)
    assert not security.verify_password(password[:-2] + "x ", hashed)


def test_legacy_bcrypt_can_be_verified_and_upgraded():
    hashed = bcrypt.hashpw(b"synthetic-password", bcrypt.gensalt(rounds=4)).decode()
    assert security.verify_password("synthetic-password", hashed)
    assert security.password_needs_rehash(hashed)
    assert not security.verify_password("wrong-password", hashed)
    assert not security.verify_password("password", "corrupt-hash")


@pytest.mark.parametrize(
    "override",
    [
        {"sub": "not-a-uuid"},
        {"iss": "https://attacker.example"},
        {"aud": "different-api"},
        {"type": "other"},
        {"exp": 1},
        {"iat": 9999999999},
    ],
)
def test_malformed_or_cross_service_claims_rejected(override):
    now = datetime.now(UTC)
    claims = {
        "sub": str(uuid4()),
        "iss": security.settings.OIDC_ISSUER_URL,
        "aud": security.settings.JWT_AUDIENCE,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=1),
        "type": "access",
    } | override
    token = jwt.encode(
        claims, security.settings.JWT_SECRET_KEY, algorithm=security.settings.JWT_ALGORITHM
    )
    with pytest.raises(HTTPException) as raised:
        security.decode_token(token)
    assert raised.value.status_code == 401


def test_security_claims_cannot_be_overridden():
    with pytest.raises(ValueError):
        security.create_access_token(uuid4(), "patient", extra_claims={"type": "refresh"})


@pytest.mark.asyncio
async def test_refresh_token_is_not_an_access_token():
    db = AsyncMock()
    with pytest.raises(HTTPException):
        await security.get_current_user(security.create_refresh_token(uuid4(), str(uuid4())), db)
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_revoked_session_rejected():
    user = SimpleNamespace(id=uuid4())
    db = AsyncMock()
    db.execute.side_effect = [
        Mock(scalar_one_or_none=Mock(return_value=user)),
        Mock(scalar_one_or_none=Mock(return_value=None)),
    ]
    with pytest.raises(HTTPException) as raised:
        await security.get_current_user(
            security.create_access_token(user.id, "patient", str(uuid4())), db
        )
    assert raised.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_session_and_rejects_replay():
    from app.services.auth_service import refresh_access_token

    session_id = str(uuid4())
    user = SimpleNamespace(id=uuid4(), role="patient")
    db = AsyncMock()
    db.execute.side_effect = [
        Mock(scalar_one_or_none=Mock(return_value=user)),
        Mock(scalar_one_or_none=Mock(return_value=uuid4())),
        Mock(scalar_one_or_none=Mock(return_value=user)),
        Mock(scalar_one_or_none=Mock(return_value=None)),
    ]
    original = security.create_refresh_token(user.id, session_id)
    result = await refresh_access_token(db, refresh_token=original)
    rotated = security.decode_token(result["tokens"].refresh_token)
    assert rotated.session_id != session_id
    assert isinstance(UUID(rotated.session_id), UUID)
    with pytest.raises(AppError) as raised:
        await refresh_access_token(db, refresh_token=original)
    assert raised.value.status_code == 401


@pytest.mark.asyncio
async def test_unverified_production_account_is_denied(monkeypatch):
    monkeypatch.setattr(security.settings, "ENVIRONMENT", Environment.PRODUCTION)
    with pytest.raises(HTTPException) as raised:
        await security.get_current_active_user(SimpleNamespace(is_active=True, is_verified=False))
    assert raised.value.status_code == 403


def test_nested_phi_redaction():
    event = {"payload": [{"password": "secret", "email": "patient@example.com", "safe": 1}]}
    assert redact_sensitive_fields(None, "info", event) == {
        "payload": [{"password": "[REDACTED]", "email": "[REDACTED]", "safe": 1}]
    }


def test_asgi_exception_logging_does_not_expose_exception_contents():
    error = ValueError("patient medical detail")
    record = logging.LogRecord(
        "uvicorn.error",
        logging.ERROR,
        __file__,
        1,
        "Exception in ASGI application",
        (),
        (ValueError, error, None),
    )
    assert ExceptionPrivacyFilter().filter(record)
    assert record.exc_info is None
    assert "patient" not in record.getMessage()
    assert "ValueError" in record.getMessage()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata",
    [
        {"ContentLength": 0, "ContentType": "application/pdf"},
        {"ContentLength": 30 * 1024 * 1024, "ContentType": "application/pdf"},
        {"ContentLength": 100, "ContentType": "text/html"},
    ],
)
async def test_upload_inspection_rejects_invalid_stored_object(monkeypatch, metadata):
    from app.core import storage

    client = Mock(head_object=Mock(return_value=metadata))
    monkeypatch.setattr(storage, "get_s3_client", Mock(return_value=client))
    with pytest.raises(AppError) as raised:
        await storage.inspect_uploaded_object("synthetic-object", "application/pdf")
    assert raised.value.status_code == 422


@pytest.mark.asyncio
async def test_upload_inspection_returns_actual_stored_size(monkeypatch):
    from app.core import storage

    client = Mock(
        head_object=Mock(return_value={"ContentLength": 256, "ContentType": "application/pdf"})
    )
    monkeypatch.setattr(storage, "get_s3_client", Mock(return_value=client))
    assert await storage.inspect_uploaded_object("synthetic-object", "application/pdf") == 256


def test_rate_limits_and_outage_fail_closed(monkeypatch):
    from app import middleware

    monkeypatch.setattr(middleware, "get_settings", lambda: Settings(_env_file=None))

    app = FastAPI()
    app.add_middleware(middleware.RateLimitMiddleware)
    app.add_middleware(middleware.RequestIDMiddleware)

    @app.post("/api/v1/auth/login")
    async def login():
        return {"ok": True}

    fake_redis = AsyncMock()
    monkeypatch.setattr(middleware, "redis_client", fake_redis)
    client = TestClient(app)
    fake_redis.eval.side_effect = [[1, 60], [11, 55]]
    response = client.post("/api/v1/auth/login", headers={"X-Request-ID": "untrusted-data"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "55"
    assert response.headers["X-Request-ID"] != "untrusted-data"
    fake_redis.eval.side_effect = ConnectionError("sensitive connection detail")
    response = client.post("/api/v1/auth/login")
    assert response.status_code == 503
    assert "sensitive" not in response.text


@pytest.mark.asyncio
async def test_account_throttle_uses_normalized_private_key(monkeypatch):
    from app.core import redis

    backend = AsyncMock()
    backend.eval.side_effect = [[1, 60], [11, 45]]
    monkeypatch.setattr(redis, "redis_client", backend)
    await redis.limit_auth_account("Patient@example.com")
    with pytest.raises(HTTPException) as raised:
        await redis.limit_auth_account("patient@example.com")
    assert raised.value.status_code == 429
    assert raised.value.headers["Retry-After"] == "45"
    first_key = backend.eval.call_args_list[0].args[2]
    assert first_key == backend.eval.call_args_list[1].args[2]
    assert "patient" not in first_key


def test_readiness_failure_returns_503_and_liveness_stays_healthy(monkeypatch):
    import app.core.database
    import app.core.redis
    import app.core.storage
    from app.main import create_application

    @asynccontextmanager
    async def failed_connection():
        raise ConnectionError("database unavailable")
        yield

    monkeypatch.setattr(app.core.database, "engine", SimpleNamespace(connect=failed_connection))
    monkeypatch.setattr(app.core.redis, "redis_client", AsyncMock())
    monkeypatch.setattr(app.core.storage, "get_s3_client", Mock(return_value=Mock()))
    client = TestClient(create_application())
    ready = client.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json()["services"]["database"] == "unhealthy"
    assert client.get("/health/live").status_code == 200


def test_http_authentication_headers_are_preserved(monkeypatch):
    from app import middleware
    from app.main import create_application

    monkeypatch.setattr(middleware, "redis_client", AsyncMock(eval=AsyncMock(return_value=[1, 60])))
    client = TestClient(create_application())
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["Cache-Control"] == "no-store"
