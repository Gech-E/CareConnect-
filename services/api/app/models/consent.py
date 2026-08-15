import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin

class ConsentType(str, enum.Enum):
    terms = "terms"
    privacy = "privacy"
    telehealth = "telehealth"
    communication = "communication"

class ConsentStatus(str, enum.Enum):
    accepted = "accepted"
    withdrawn = "withdrawn"

class Consent(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "consents"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    consent_type: Mapped[ConsentType] = mapped_column(Enum(ConsentType), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ConsentStatus] = mapped_column(Enum(ConsentStatus), default=ConsentStatus.accepted, index=True, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(45))
