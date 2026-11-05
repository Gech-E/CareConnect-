import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin

class ThreadStatus(str, enum.Enum):
    active = "active"
    archived = "archived"
    closed = "closed"

class MessageStatus(str, enum.Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"

class MessageThread(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "message_threads"

    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id", ondelete="SET NULL"), index=True)
    subject: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ThreadStatus] = mapped_column(Enum(ThreadStatus), default=ThreadStatus.active, index=True, nullable=False)

    participants: Mapped[list["MessageThreadParticipant"]] = relationship("MessageThreadParticipant", back_populates="thread")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="thread")

class MessageThreadParticipant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "message_thread_participants"

    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("message_threads.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    role: Mapped[str | None] = mapped_column(String(50))

    thread: Mapped["MessageThread"] = relationship("MessageThread", back_populates="participants")

class Message(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "messages"

    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("message_threads.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[MessageStatus] = mapped_column(Enum(MessageStatus), default=MessageStatus.sent, nullable=False)
    attachment_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    thread: Mapped["MessageThread"] = relationship("MessageThread", back_populates="messages")
