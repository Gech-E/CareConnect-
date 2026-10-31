"""SQLAlchemy declarative base and common model mixins.

All models inherit from Base and use UUID primary keys with
UTC timestamps as required by SRS §6.2.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all CareConnect ORM models."""

    pass


class TimestampMixin:
    """Adds created_at and updated_at columns with UTC enforcement."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        nullable=False,
    )


class UUIDMixin:
    """Adds a UUID primary key (non-sequential, opaque per SRS §6.2)."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class SoftDeleteMixin:
    """Adds soft-delete support (SRS §6.2: retention/audit history)."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "SoftDeleteMixin",
]
