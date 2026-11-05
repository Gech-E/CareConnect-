"""CareConnect Telehealth Platform — Main FastAPI Application.

Production-grade entry point with middleware stack, error handlers,
CORS configuration, and health checks per SRS requirements.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

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
            ensure_bucket_exists()
            logger.info("storage.bucket_ready")
        except Exception as e:
            logger.warning("storage.bucket_init_failed", error=str(e))

    yield

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info("application.shutting_down")

    # Close Redis pool
    try:
        from app.core.redis import redis_pool
        await redis_pool.aclose()
    except Exception:
        pass

    # Dispose database engine
    try:
        from app.core.database import engine
        await engine.dispose()
    except Exception:
        pass


def create_application() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "CareConnect Telehealth Platform API. "
            "Designed to support a HIPAA-compliant deployment. "
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

    # ── Middleware (order matters: first added = outermost) ───────
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
    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check() -> HealthResponse:
        """System health check endpoint."""
        services = {}

        # Check database
        try:
            from app.core.database import engine
            async with engine.connect() as conn:
                await conn.execute(
                    __import__("sqlalchemy").text("SELECT 1")
                )
            services["database"] = "healthy"
        except Exception:
            services["database"] = "unhealthy"

        # Check Redis
        try:
            from app.core.redis import redis_client
            await redis_client.ping()
            services["redis"] = "healthy"
        except Exception:
            services["redis"] = "unhealthy"

        # Check S3
        try:
            from app.core.storage import get_s3_client
            client = get_s3_client()
            client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
            services["storage"] = "healthy"
        except Exception:
            services["storage"] = "unhealthy"

        overall = "ok" if all(s == "healthy" for s in services.values()) else "degraded"

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
            "docs": "/docs",
            "health": "/health",
            "api": settings.API_V1_PREFIX,
        }

    return app


# Create the application instance
app = create_application()
