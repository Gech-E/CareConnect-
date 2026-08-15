import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Enum, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin

class NotificationChannel(str, enum.Enum):
    in_app = "in_app"
    push = "push"
    email = "email"
    sms = "sms"

class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    delivered = "delivered"
    failed = "failed"
    read = "read"

class Notification(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "notifications"

    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), index=True, nullable=False)
    template_key: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str | None] = mapped_column(String(255))
    body_preview: Mapped[str | None] = mapped_column(String(500))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.pending, index=True, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500))
