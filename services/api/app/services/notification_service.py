"""Notification management service.

Handles listing, marking as read, and creating notifications.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)


async def get_user_notifications(
    db: AsyncSession, 
    user_id: UUID, 
    limit: int = 20, 
    cursor: str | None = None
) -> dict:
    """List notifications with pagination."""
    from app.models.notification import Notification

    query = select(Notification).where(Notification.recipient_id == user_id)
    query = query.order_by(Notification.created_at.desc()).limit(limit + 1)
    
    if cursor:
        from uuid import UUID as UUIDType
        query = query.where(Notification.id < UUIDType(cursor))
        
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    has_more = len(notifications) > limit
    if has_more:
        notifications = notifications[:limit]
        
    return {
        "items": [
            {
                "id": str(n.id),
                "recipient_id": str(n.recipient_id),
                "channel": n.channel,
                "template_key": n.template_key,
                "subject": n.subject,
                "body_preview": n.body_preview,
                "status": n.status,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "read_at": n.read_at.isoformat() if n.read_at else None,
            }
            for n in notifications
        ],
        "next_cursor": str(notifications[-1].id) if has_more else None,
        "has_more": has_more,
    }


async def mark_notification_read(db: AsyncSession, notification_id: UUID, user_id: UUID) -> dict:
    """Mark as read."""
    from app.models.notification import Notification, NotificationStatus

    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.recipient_id == user_id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise NotFoundError("notification")
        
    notification.status = NotificationStatus.read
    notification.read_at = datetime.now(UTC)
    await db.flush()
    
    return {
        "id": str(notification.id),
        "status": notification.status,
        "read_at": notification.read_at.isoformat(),
    }


async def create_notification(
    db: AsyncSession, 
    recipient_id: UUID, 
    channel: str, 
    template_key: str | None, 
    subject: str | None, 
    body_preview: str | None, 
    payload: dict
) -> dict:
    """Create notification record and optionally queue for delivery."""
    from app.models.notification import Notification

    notification = Notification(
        recipient_id=recipient_id,
        channel=channel,
        template_key=template_key,
        subject=subject,
        body_preview=body_preview,
        payload=payload,
    )
    db.add(notification)
    await db.flush()
    
    # Optionally queue for delivery using celery or similar task here
    
    return {
        "id": str(notification.id),
        "status": notification.status,
    }
