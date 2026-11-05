import enum
import uuid
from sqlalchemy import String, Enum, ForeignKey, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin

class PractitionerStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    inactive = "inactive"

class OrganizationType(str, enum.Enum):
    clinic = "clinic"
    hospital = "hospital"
    private_practice = "private_practice"
    health_system = "health_system"

class Organization(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[OrganizationType | None] = mapped_column(Enum(OrganizationType))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    practitioner_roles: Mapped[list["PractitionerRole"]] = relationship("PractitionerRole", back_populates="organization")

class Practitioner(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "practitioners"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    credentials: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(String)
    years_of_experience: Mapped[int | None] = mapped_column(Integer)
    profile_image_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[PractitionerStatus] = mapped_column(Enum(PractitionerStatus), default=PractitionerStatus.active, index=True, nullable=False)
    average_rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    roles: Mapped[list["PractitionerRole"]] = relationship("PractitionerRole", back_populates="practitioner")

class PractitionerRole(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "practitioner_roles"

    practitioner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practitioners.id", ondelete="CASCADE"), index=True, nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(255))
    languages: Mapped[list[str]] = mapped_column(JSONB, default=list)
    service_areas: Mapped[list[str]] = mapped_column(JSONB, default=list)
    visit_types: Mapped[list[str]] = mapped_column(JSONB, default=list)
    price_range_min: Mapped[float | None] = mapped_column(Float)
    price_range_max: Mapped[float | None] = mapped_column(Float)

    practitioner: Mapped["Practitioner"] = relationship("Practitioner", back_populates="roles")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="practitioner_roles")
