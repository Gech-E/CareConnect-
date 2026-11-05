import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class RecordType(enum.StrEnum):
    lab_result = "lab_result"
    diagnostic_report = "diagnostic_report"
    clinical_note = "clinical_note"
    imaging = "imaging"
    discharge_summary = "discharge_summary"
    other = "other"


class RecordStatus(enum.StrEnum):
    available = "available"
    pending = "pending"
    unavailable = "unavailable"
    archived = "archived"


class DocumentContextType(enum.StrEnum):
    appointment = "appointment"
    encounter = "encounter"
    record = "record"
    prescription = "prescription"
    message = "message"
    profile = "profile"


class ScanStatus(enum.StrEnum):
    pending = "pending"
    clean = "clean"
    infected = "infected"
    error = "error"


class MedicalRecord(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "medical_records"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    record_type: Mapped[RecordType] = mapped_column(Enum(RecordType), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(100))
    source_id: Mapped[str | None] = mapped_column(String(255))
    service_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus), default=RecordStatus.available, index=True, nullable=False
    )
    fhir_resource_type: Mapped[str | None] = mapped_column(String(100))
    fhir_resource_id: Mapped[str | None] = mapped_column(String(255))


class Document(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "documents"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    context_type: Mapped[DocumentContextType] = mapped_column(
        Enum(DocumentContextType), index=True, nullable=False
    )
    context_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(255))
    scan_status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus), default=ScanStatus.pending, nullable=False
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
