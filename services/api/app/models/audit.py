import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base, UUIDMixin

class AuditOutcome(str, enum.Enum):
    success = "success"
    failure = "failure"
    denied = "denied"

class AuditEvent(Base, UUIDMixin):
    __tablename__ = "audit_events"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    actor_role: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    purpose: Mapped[str | None] = mapped_column(String(255))
    outcome: Mapped[AuditOutcome] = mapped_column(Enum(AuditOutcome), index=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    request_id: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True, nullable=False)
