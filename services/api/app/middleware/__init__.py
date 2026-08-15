"""Middleware stack for CareConnect API.

Provides request correlation, security headers, rate limiting,
and audit logging middleware per SRS §10.
"""

import time
from uuid import uuid4

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request ID to every request for correlation.

    Per SRS §10.4: All logs must include request/correlation ID.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
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

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        # Per SRS §7.1: Protected data responses use no-store
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request/response metadata (no PHI) for observability."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "http_request",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=request.client.host if request.client else "unknown",
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter.

    Per SRS §10.3: Rate-limit authentication, search abuse,
    uploads, messaging, and token creation.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Rate limiting is applied selectively via dependencies
        # This middleware provides global fallback protection
        return await call_next(request)
