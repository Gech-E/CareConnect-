import enum
import uuid
from datetime import date, datetime
from sqlalchemy import String, Boolean, Enum, ForeignKey, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from app.models import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin

class VerificationStatus(str, enum.Enum):
    unverified = "unverified"
    verified = "verified"
    failed = "failed"

class PatientProfile(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "patient_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    legal_first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    legal_last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(50))
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str | None] = mapped_column(String(100))
    timezone: Mapped[str | None] = mapped_column(String(50))
    preferred_language: Mapped[str | None] = mapped_column(String(50))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(50))
    communication_pref_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    communication_pref_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    communication_pref_push: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="patient_profile")
    insurance_policies: Mapped[list["InsurancePolicy"]] = relationship("InsurancePolicy", back_populates="patient", primaryjoin="PatientProfile.user_id == foreign(InsurancePolicy.patient_id)")

class InsurancePolicy(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "insurance_policies"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    payer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    member_id: Mapped[str] = mapped_column(String(100), nullable=False)
    group_number: Mapped[str | None] = mapped_column(String(100))
    plan_name: Mapped[str | None] = mapped_column(String(255))
    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus), default=VerificationStatus.unverified, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    patient: Mapped["PatientProfile"] = relationship("PatientProfile", back_populates="insurance_policies", primaryjoin="PatientProfile.user_id == foreign(InsurancePolicy.patient_id)")
