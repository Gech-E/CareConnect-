import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Enum, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin

class AppointmentStatus(str, enum.Enum):
    draft = "draft"
    held = "held"
    confirmed = "confirmed"
    checked_in = "checked_in"
    waiting = "waiting"
    in_progress = "in_progress"
    completed = "completed"
    rescheduled = "rescheduled"
    cancelled_by_patient = "cancelled_by_patient"
    cancelled_by_clinician = "cancelled_by_clinician"
    no_show = "no_show"
    expired = "expired"

class Appointment(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "appointments"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    practitioner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practitioners.id", ondelete="CASCADE"), index=True, nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True)
    visit_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(Enum(AppointmentStatus), index=True, nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str | None] = mapped_column(String(50), default="UTC")
    cancellation_reason: Mapped[str | None] = mapped_column(String(255))
    rescheduled_from_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id", ondelete="SET NULL"))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    preparation_instructions: Mapped[str | None] = mapped_column(String)
    estimated_price: Mapped[float | None] = mapped_column(Float)

    history: Mapped[list["AppointmentStatusHistory"]] = relationship("AppointmentStatusHistory", back_populates="appointment")

class AppointmentStatusHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "appointment_status_history"

    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), index=True, nullable=False)
    from_status: Mapped[AppointmentStatus | None] = mapped_column(Enum(AppointmentStatus))
    to_status: Mapped[AppointmentStatus] = mapped_column(Enum(AppointmentStatus), nullable=False)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(String(255))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="history")
