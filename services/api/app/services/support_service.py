"""Support management service.

Handles creating and managing support cases.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)


async def create_support_case(
    db: AsyncSession, 
    subject_user_id: UUID, 
    category: str, 
    notes: str | None, 
    ip_address: str | None = None
) -> dict:
    """Create support case."""
    from app.models.support import SupportCase

    case = SupportCase(
        subject_user_id=subject_user_id,
        category=category,
        notes=notes,
        opened_at=datetime.now(UTC),
    )
    db.add(case)
    await db.flush()

    await log_audit_event(
        db,
        actor_id=subject_user_id,
        actor_role="user",
        action="support_case.created",
        resource_type="support_case",
        resource_id=case.id,
        ip_address=ip_address,
        metadata={"category": category}
    )

    return {
        "id": str(case.id),
        "subject_user_id": str(case.subject_user_id),
        "category": case.category,
        "status": case.status,
        "priority": case.priority,
        "opened_at": case.opened_at.isoformat(),
    }


async def get_support_cases(
    db: AsyncSession, 
    user_id: UUID, 
    limit: int = 20, 
    cursor: str | None = None
) -> dict:
    """List user's support cases."""
    from app.models.support import SupportCase

    query = select(SupportCase).where(SupportCase.subject_user_id == user_id)
    query = query.order_by(SupportCase.created_at.desc()).limit(limit + 1)
    
    if cursor:
        from uuid import UUID as UUIDType
        query = query.where(SupportCase.id < UUIDType(cursor))
        
    result = await db.execute(query)
    cases = result.scalars().all()
    
    has_more = len(cases) > limit
    if has_more:
        cases = cases[:limit]
        
    return {
        "items": [
            {
                "id": str(c.id),
                "category": c.category,
                "status": c.status,
                "priority": c.priority,
                "opened_at": c.opened_at.isoformat() if c.opened_at else None,
                "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
            }
            for c in cases
        ],
        "next_cursor": str(cases[-1].id) if has_more else None,
        "has_more": has_more,
    }


async def update_support_case(
    db: AsyncSession, 
    case_id: UUID, 
    status: str | None = None, 
    notes: str | None = None, 
    assigned_to_id: UUID | None = None
) -> dict:
    """Update case status."""
    from app.models.support import SupportCase, SupportStatus

    result = await db.execute(
        select(SupportCase).where(SupportCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise NotFoundError("support case")
        
    if status is not None:
        case.status = status
        if status in (SupportStatus.resolved, SupportStatus.closed):
            case.resolved_at = datetime.now(UTC)
            
    if notes is not None:
        case.notes = notes
        
    if assigned_to_id is not None:
        case.assigned_to_id = assigned_to_id
        
    await db.flush()

    return {
        "id": str(case.id),
        "status": case.status,
        "assigned_to_id": str(case.assigned_to_id) if case.assigned_to_id else None,
        "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
    }
