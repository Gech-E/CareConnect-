"""Shared Pydantic schema utilities and base classes."""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class CareConnectBase(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        json_schema_extra={"examples": []},
    )


class TimestampSchema(CareConnectBase):
    """Schema mixin for timestamp fields."""

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Cursor-based pagination parameters (SRS §7.1)."""

    cursor: str | None = Field(None, description="Opaque cursor for pagination")
    limit: int = Field(20, ge=1, le=100, description="Number of items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""

    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    total_count: int | None = None


class ErrorDetail(BaseModel):
    """Single validation error detail."""

    field: str
    message: str
    type: str = ""


class ErrorResponse(BaseModel):
    """Standard error response per SRS §7.1 / RFC 7807."""

    error: dict[str, Any] = Field(
        ...,
        examples=[
            {
                "code": "APPOINTMENT_SLOT_UNAVAILABLE",
                "message": "That time is no longer available.",
                "request_id": "abc-123",
                "details": {},
            }
        ],
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str
    environment: str
    services: dict[str, str] = {}
