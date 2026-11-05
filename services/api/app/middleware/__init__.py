"""Middleware stack for CareConnect API.

Provides request correlation, security headers, rate limiting,
and audit logging middleware per SRS §10.
"""

import time
from hashlib import sha256
from uuid import UUID, uuid4

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core import get_settings
from app.core.exceptions import AppError, app_error_handler
from app.core.redis import RATE_LIMIT_SCRIPT, redis_client

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request ID to every request for correlation.

    Per SRS §10.4: All logs must include request/correlation ID.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            request_id = str(UUID(request.headers.get("X-Request-ID", "")))
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all responses.

    Per SRS §10.3: Configure secure headers and content security policy.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # Per SRS §7.1: Protected data responses use no-store
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request/response metadata (no PHI) for observability."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "http_request",
            method=request.method,
            route=getattr(request.scope.get("route"), "path", "<unmatched>"),
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Atomic Redis fixed-window rate limits shared by all API workers.

    Per SRS §10.3: Rate-limit authentication, search abuse,
    uploads, messaging, and token creation.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        path = request.url.path
        if request.method == "OPTIONS" or not path.startswith(settings.API_V1_PREFIX + "/"):
            return await call_next(request)

        # Only trust the ASGI peer. Forwarded headers must be validated by the
        # reverse proxy/Uvicorn trusted-proxy configuration before reaching here.
        peer = request.client.host if request.client else "unknown"
        identity = sha256(peer.encode()).hexdigest()
        budgets = [("api", settings.RATE_LIMIT_API_PER_MINUTE)]
        if path.startswith(settings.API_V1_PREFIX + "/auth/"):
            budgets.append(("auth", settings.RATE_LIMIT_AUTH_PER_MINUTE))
        if "upload" in path:
            budgets.append(("upload", settings.RATE_LIMIT_UPLOAD_PER_MINUTE))
        try:
            for category, limit in budgets:
                count, ttl = await redis_client.eval(
                    RATE_LIMIT_SCRIPT, 1, f"rate-limit:{category}:{identity}", 60
                )
                if count > limit:
                    response = await app_error_handler(
                        request,
                        AppError(
                            "RATE_LIMIT_EXCEEDED", "Too many requests. Please try again later.", 429
                        ),
                    )
                    response.headers["Retry-After"] = str(max(int(ttl), 1))
                    return response
        except Exception:
            # Authentication protection must not disappear during a Redis outage.
            logger.error("rate_limit_backend_unavailable")
            response = await app_error_handler(
                request,
                AppError(
                    "SERVICE_UNAVAILABLE",
                    "Service temporarily unavailable. Please try again later.",
                    503,
                ),
            )
            response.headers["Retry-After"] = "30"
            return response
        return await call_next(request)
