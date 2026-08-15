import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin

class SupportCategory(str, enum.Enum):
    account = "account"
    billing = "billing"
    technical = "technical"
    clinical = "clinical"
    other = "other"

class SupportStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"

class SupportPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class SupportCase(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "support_cases"

    subject_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    category: Mapped[SupportCategory] = mapped_column(Enum(SupportCategory), index=True, nullable=False)
    status: Mapped[SupportStatus] = mapped_column(Enum(SupportStatus), default=SupportStatus.open, index=True, nullable=False)
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    priority: Mapped[SupportPriority] = mapped_column(Enum(SupportPriority), default=SupportPriority.medium, index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
