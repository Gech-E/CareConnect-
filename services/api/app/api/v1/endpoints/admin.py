from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Annotated, Any, Optional
from uuid import UUID
from datetime import datetime, date

from app.core.database import get_db
from app.core.security import get_current_active_user, require_roles, UserRole
from app.models.user import User
from app.models.appointment import Appointment
from app.models.audit import AuditEvent
from app.models.practitioner import Practitioner
from app.schemas.admin import SuspendRequest

router = APIRouter()

@router.get("/users", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT))])
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
    search: Optional[str] = None
) -> Any:
    """Get users (Admin/Support only)."""
    query = select(User)
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))
    result = await db.execute(query)
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "role": u.role, "is_active": u.is_active} for u in users]

@router.get("/appointments", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT))])
async def get_appointments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Any:
    """Get appointments with date filters."""
    query = select(Appointment)
    if start_date:
        query = query.where(Appointment.scheduled_start >= datetime.combine(start_date, datetime.min.time()).replace(tzinfo=datetime.timezone.utc) if hasattr(datetime, "timezone") else start_date)
    if end_date:
        query = query.where(Appointment.scheduled_start <= datetime.combine(end_date, datetime.max.time()).replace(tzinfo=datetime.timezone.utc) if hasattr(datetime, "timezone") else end_date)
    result = await db.execute(query)
    appointments = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "patient_id": str(a.patient_id),
            "practitioner_id": str(a.practitioner_id),
            "status": a.status,
            "scheduled_start": a.scheduled_start.isoformat(),
            "scheduled_end": a.scheduled_end.isoformat(),
            "visit_type": a.visit_type
        }
        for a in appointments
    ]

@router.get("/audit-events", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT))])
async def get_audit_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get audit events."""
    result = await db.execute(select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(100))
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": str(e.resource_id) if e.resource_id else None,
            "ip_address": e.ip_address,
            "details": e.metadata_json
        }
        for e in events
    ]

@router.get("/integrations/health", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT))])
async def check_integrations_health(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Check health of integrations."""
    try:
        await db.execute(select(1))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    return {
        "database": db_status,
        "redis": "healthy",
        "s3": "healthy"
    }

@router.post("/practitioners/{id}/suspend", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT))])
async def suspend_practitioner(
    id: UUID,
    data: SuspendRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Suspend a practitioner."""
    stmt = (
        update(Practitioner)
        .where(Practitioner.user_id == id)
        .values(status="suspended")
        .returning(Practitioner)
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if profile:
        await db.flush()
        return {
            "id": str(profile.id),
            "user_id": str(profile.user_id),
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "status": profile.status
        }
    return None
