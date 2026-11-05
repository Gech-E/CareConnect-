import enum
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Enum, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base, TimestampMixin, UUIDMixin, SoftDeleteMixin

class EncounterStatus(str, enum.Enum):
    created = "created"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

class VideoSessionStatus(str, enum.Enum):
    created = "created"
    token_issued = "token_issued"
    joining = "joining"
    connected = "connected"
    reconnecting = "reconnecting"
    failed = "failed"
    ended = "ended"

class Encounter(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "encounters"

    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    status: Mapped[EncounterStatus] = mapped_column(Enum(EncounterStatus), default=EncounterStatus.created, index=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

class VideoSession(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "video_sessions"

    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), index=True, nullable=False)
    vendor_session_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[VideoSessionStatus] = mapped_column(Enum(VideoSessionStatus), default=VideoSessionStatus.created, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    participant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
