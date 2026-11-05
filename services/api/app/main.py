"""CareConnect Telehealth Platform — Main FastAPI Application.

Production-grade entry point with middleware stack, error handlers,
CORS configuration, and health checks per SRS requirements.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from app.core import get_settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_error_handler,
)
from app.core.logging import setup_logging
from app.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.schemas import HealthResponse

settings = get_settings()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # ── Startup ──────────────────────────────────────────────────
    setup_logging("DEBUG" if settings.DEBUG else "INFO")
    logger.info(
        "application.starting",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT.value,
    )

    # Ensure S3 bucket exists (local dev)
    if settings.is_local:
        try:
            from app.core.storage import ensure_bucket_exists

            await run_in_threadpool(ensure_bucket_exists)
            logger.info("storage.bucket_ready")
        except Exception:
            logger.warning("storage.bucket_init_failed")

    try:
        yield
    finally:
        logger.info("application.shutting_down")
        from app.core.database import engine
        from app.core.redis import redis_client, redis_pool
        from app.core.storage import get_s3_client

        await redis_client.aclose()
        await redis_pool.aclose()
        await engine.dispose()
        get_s3_client().close()
        get_s3_client.cache_clear()


def create_application() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    from app.models import register_models

    register_models()
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "CareConnect Telehealth Platform API. "
            "This API provides patient registration, clinician discovery, "
            "appointment scheduling, video consultations, secure messaging, "
            "medical records, and prescription management."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Middleware wraps in reverse registration order (last added = outermost).
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ── Error handlers ───────────────────────────────────────────
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # ── Routes ───────────────────────────────────────────────────
    from app.api.v1 import api_router

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ── Health check ─────────────────────────────────────────────
    @app.get("/health/live", tags=["System"])
    async def liveness() -> dict[str, str]:
        """Process health independent of downstream service outages."""
        return {"status": "ok"}

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    @app.get("/health/ready", response_model=HealthResponse, tags=["System"])
    async def health_check(response: Response) -> HealthResponse:
        """Bounded readiness checks; dependencies failing produces HTTP 503."""

        async def database_check() -> None:
            from app.core.database import engine

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        async def redis_check() -> None:
            from app.core.redis import redis_client

            await redis_client.ping()

        async def storage_check() -> None:
            from app.core.storage import get_s3_client

            await asyncio.to_thread(get_s3_client().head_bucket, Bucket=settings.S3_BUCKET_NAME)

        checks = {"database": database_check, "redis": redis_check, "storage": storage_check}
        results = await asyncio.gather(
            *(asyncio.wait_for(check(), timeout=5) for check in checks.values()),
            return_exceptions=True,
        )
        services = {
            name: "unhealthy" if isinstance(result, BaseException) else "healthy"
            for name, result in zip(checks, results, strict=True)
        }

        overall = "ok" if all(s == "healthy" for s in services.values()) else "degraded"
        response.status_code = 200 if overall == "ok" else 503
        response.headers["Cache-Control"] = "no-store"

        return HealthResponse(
            status=overall,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT.value,
            services=services,
        )

    @app.get("/", tags=["System"])
    async def root():
        """API root — returns basic info."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": None if settings.is_production else "/docs",
            "health": "/health",
            "api": settings.API_V1_PREFIX,
        }

    return app


# Create the application instance
app = create_application()
