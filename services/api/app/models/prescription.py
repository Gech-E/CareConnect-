import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class PrescriptionStatus(enum.StrEnum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"
    on_hold = "on_hold"


class FulfillmentDeliveryMethod(enum.StrEnum):
    pickup = "pickup"
    delivery = "delivery"


class FulfillmentStatus(enum.StrEnum):
    not_requested = "not_requested"
    requested = "requested"
    accepted = "accepted"
    processing = "processing"
    ready = "ready"
    dispatched = "dispatched"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Prescription(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "prescriptions"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    prescriber_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practitioners.id", ondelete="CASCADE"), index=True, nullable=False
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("encounters.id", ondelete="SET NULL"), index=True
    )
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False)
    strength: Mapped[str | None] = mapped_column(String(100))
    form: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[str | None] = mapped_column(String(100))
    instructions: Mapped[str | None] = mapped_column(Text)
    refills_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refills_remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[PrescriptionStatus] = mapped_column(
        Enum(PrescriptionStatus), default=PrescriptionStatus.active, index=True, nullable=False
    )
    prescribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_controlled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(100))
    source_id: Mapped[str | None] = mapped_column(String(255))


class FulfillmentRequest(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "fulfillment_requests"

    prescription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pharmacy_name: Mapped[str | None] = mapped_column(String(255))
    pharmacy_address: Mapped[str | None] = mapped_column(String(500))
    delivery_method: Mapped[FulfillmentDeliveryMethod] = mapped_column(
        Enum(FulfillmentDeliveryMethod), nullable=False
    )
    status: Mapped[FulfillmentStatus] = mapped_column(
        Enum(FulfillmentStatus), default=FulfillmentStatus.not_requested, index=True, nullable=False
    )
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_reference: Mapped[str | None] = mapped_column(String(255))
