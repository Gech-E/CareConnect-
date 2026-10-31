import uuid
from datetime import time, date
from sqlalchemy import String, Boolean, ForeignKey, Time, Date, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin

class AvailabilityRule(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "availability_rules"

    practitioner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practitioners.id", ondelete="CASCADE"), index=True, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False) # 0-6
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    visit_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class AvailabilityException(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "availability_exceptions"

    practitioner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practitioners.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    reason: Mapped[str | None] = mapped_column(String(255))
