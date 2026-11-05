"""Audit service for append-only event logging.

Per SRS §10.4: Record actor, action, resource, purpose/reason,
timestamp, source, and outcome for all sensitive operations.
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


async def log_audit_event(
    db: AsyncSession,
    *,
    actor_id: UUID | None,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    purpose: str | None = None,
    outcome: str = "success",
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Create an append-only audit event.

    This function must never raise — audit failures are logged
    but must not break the primary operation.
    """
    try:
        from app.models.audit import AuditEvent

        event = AuditEvent(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            purpose=purpose,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata_json=metadata or {},
        )
        db.add(event)
        # Flush immediately — audit events should not be lost on rollback
        await db.flush()
    except Exception:
        logger.error(
            "audit_event_failed",
            action=action,
            resource_type=resource_type,
            exc_info=True,
        )
