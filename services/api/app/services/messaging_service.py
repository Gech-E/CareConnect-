"""Messaging service for secure threads and messages.

Implements SRS §4.8: scoped threads, delivery status,
read tracking, and PHI-safe notification handling.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)


async def create_thread(
    db: AsyncSession,
    *,
    creator_id: UUID,
    creator_role: str,
    participant_ids: list[UUID],
    appointment_id: UUID | None = None,
    subject: str | None = None,
    ip_address: str | None = None,
) -> dict:
    """Create a new message thread (MSG-001, MSG-002)."""
    from app.models.messaging import Message, MessageThread, MessageThreadParticipant

    # Ensure creator is in participants
    all_participants = list(set([creator_id] + participant_ids))

    thread = MessageThread(
        appointment_id=appointment_id,
        subject=subject or "New conversation",
        status="active",
    )
    db.add(thread)
    await db.flush()

    for uid in all_participants:
        participant = MessageThreadParticipant(
            thread_id=thread.id,
            user_id=uid,
            role="creator" if uid == creator_id else "participant",
        )
        db.add(participant)

    await db.flush()

    await log_audit_event(
        db,
        actor_id=creator_id,
        actor_role=creator_role,
        action="thread.created",
        resource_type="message_thread",
        resource_id=thread.id,
        ip_address=ip_address,
    )

    return {
        "id": str(thread.id),
        "subject": thread.subject,
        "status": thread.status,
        "appointment_id": str(thread.appointment_id) if thread.appointment_id else None,
        "participants": [str(uid) for uid in all_participants],
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
    }


async def get_user_threads(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
    cursor: str | None = None,
) -> dict:
    """List threads for a user."""
    from app.models.messaging import MessageThread, MessageThreadParticipant

    stmt = (
        select(MessageThread)
        .join(MessageThreadParticipant)
        .where(MessageThreadParticipant.user_id == user_id)
        .where(MessageThread.status != "closed")
        .order_by(MessageThread.updated_at.desc())
        .limit(limit + 1)
    )

    result = await db.execute(stmt)
    threads = result.scalars().all()

    has_more = len(threads) > limit
    if has_more:
        threads = threads[:limit]

    return {
        "items": [
            {
                "id": str(t.id),
                "subject": t.subject,
                "status": t.status,
                "appointment_id": str(t.appointment_id) if t.appointment_id else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in threads
        ],
        "next_cursor": str(threads[-1].id) if has_more else None,
        "has_more": has_more,
    }


async def send_message(
    db: AsyncSession,
    *,
    thread_id: UUID,
    sender_id: UUID,
    sender_role: str,
    body: str,
    attachment_document_id: UUID | None = None,
    ip_address: str | None = None,
) -> dict:
    """Send a message in a thread (MSG-001)."""
    from app.models.messaging import Message, MessageThread, MessageThreadParticipant

    # Verify sender is a participant
    participant_check = await db.execute(
        select(MessageThreadParticipant).where(
            MessageThreadParticipant.thread_id == thread_id,
            MessageThreadParticipant.user_id == sender_id,
        )
    )
    if not participant_check.scalar_one_or_none():
        raise ForbiddenError("You are not a participant in this thread.")

    message = Message(
        thread_id=thread_id,
        sender_id=sender_id,
        body=body,
        status="sent",
        attachment_document_id=attachment_document_id,
    )
    db.add(message)

    # Update thread timestamp
    await db.execute(
        update(MessageThread)
        .where(MessageThread.id == thread_id)
        .values(updated_at=datetime.now(UTC))
    )

    await db.flush()

    await log_audit_event(
        db,
        actor_id=sender_id,
        actor_role=sender_role,
        action="message.sent",
        resource_type="message",
        resource_id=message.id,
        ip_address=ip_address,
    )

    return {
        "id": str(message.id),
        "thread_id": str(thread_id),
        "sender_id": str(sender_id),
        "body": body,
        "status": message.status,
        "sent_at": message.sent_at.isoformat() if message.sent_at else None,
    }


async def get_thread_messages(
    db: AsyncSession,
    thread_id: UUID,
    user_id: UUID,
    limit: int = 50,
    cursor: str | None = None,
) -> dict:
    """Get messages in a thread with authorization check."""
    from app.models.messaging import Message, MessageThreadParticipant

    # Authorization
    participant_check = await db.execute(
        select(MessageThreadParticipant).where(
            MessageThreadParticipant.thread_id == thread_id,
            MessageThreadParticipant.user_id == user_id,
        )
    )
    if not participant_check.scalar_one_or_none():
        raise ForbiddenError("You are not a participant in this thread.")

    stmt = (
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.sent_at.desc())
        .limit(limit + 1)
    )

    result = await db.execute(stmt)
    messages = result.scalars().all()

    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    return {
        "items": [
            {
                "id": str(m.id),
                "sender_id": str(m.sender_id),
                "body": m.body,
                "status": m.status,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                "read_at": m.read_at.isoformat() if m.read_at else None,
            }
            for m in messages
        ],
        "next_cursor": str(messages[-1].id) if has_more else None,
        "has_more": has_more,
    }


async def mark_messages_read(
    db: AsyncSession,
    thread_id: UUID,
    user_id: UUID,
) -> None:
    """Mark all messages in a thread as read for this user (MSG-003)."""
    from app.models.messaging import Message, MessageThreadParticipant

    # Authorization
    participant_check = await db.execute(
        select(MessageThreadParticipant).where(
            MessageThreadParticipant.thread_id == thread_id,
            MessageThreadParticipant.user_id == user_id,
        )
    )
    if not participant_check.scalar_one_or_none():
        raise ForbiddenError("You are not a participant in this thread.")

    now = datetime.now(UTC)
    await db.execute(
        update(Message)
        .where(
            Message.thread_id == thread_id,
            Message.sender_id != user_id,
            Message.read_at.is_(None),
        )
        .values(read_at=now, status="read")
    )
