"""Centralized error handling with RFC 7807 Problem Details.

Per SRS §7.1: Errors use a consistent structure with human-readable
messages and machine-readable codes. No secrets, stack traces, or
protected information in error responses.
"""

from typing import Any
from uuid import uuid4

import structlog
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class AppError(Exception):
    """Base application error with RFC 7807 structure."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str, resource_id: str | None = None) -> None:
        super().__init__(
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"{resource} not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(AppError):
    """Resource state conflict (e.g., double booking, invalid state transition)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )


class ForbiddenError(AppError):
    """Authorization denied."""

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class RateLimitError(AppError):
    """Rate limit exceeded."""

    def __init__(self) -> None:
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class SlotUnavailableError(ConflictError):
    """Appointment slot is no longer available."""

    def __init__(self) -> None:
        super().__init__(
            code="APPOINTMENT_SLOT_UNAVAILABLE",
            message="That time is no longer available.",
        )


class InvalidStateTransitionError(ConflictError):
    """Invalid state machine transition."""

    def __init__(self, resource: str, from_status: str, to_status: str) -> None:
        super().__init__(
            code=f"{resource.upper()}_INVALID_TRANSITION",
            message=f"Cannot transition {resource} from '{from_status}' to '{to_status}'.",
        )


def _build_error_response(
    code: str,
    message: str,
    status_code: int,
    request_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the standard error response body."""
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details or {},
        }
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle application errors with the standard error structure."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    logger.warning(
        "app_error",
        code=exc.code,
        status_code=exc.status_code,
        request_id=request_id,
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            exc.code, exc.message, exc.status_code, request_id, exc.details
        ),
        headers={"Cache-Control": "no-store"},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI/Starlette HTTPExceptions."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            "HTTP_ERROR",
            str(exc.detail),
            exc.status_code,
            request_id,
        ),
        headers={"Cache-Control": "no-store"},
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with sanitized output."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    # Sanitize: remove 'input' from errors to avoid logging user data
    errors = []
    for error in exc.errors():
        sanitized = {
            "field": " -> ".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", ""),
        }
        errors.append(sanitized)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_error_response(
            "VALIDATION_ERROR",
            "Request validation failed.",
            422,
            request_id,
            {"errors": errors},
        ),
        headers={"Cache-Control": "no-store"},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never expose internals."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    logger.error(
        "unhandled_exception",
        exc_type=type(exc).__name__,
        request_id=request_id,
        path=str(request.url.path),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please contact support.",
            500,
            request_id,
        ),
        headers={"Cache-Control": "no-store"},
    )
