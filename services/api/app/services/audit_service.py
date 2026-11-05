"""Audit service for append-only event logging.

Per SRS §10.4: Record actor, action, resource, purpose/reason,
timestamp, source, and outcome for all sensitive operations.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


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
    """Persist an audit event atomically with the protected operation.

    Both the operation and its audit record commit or roll back together.
    Failure must propagate; silently continuing would permit unaudited changes.
    """
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
    await db.flush()
