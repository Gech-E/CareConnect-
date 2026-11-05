from datetime import UTC, date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppError, NotFoundError
from app.core.security import UserRole, get_current_active_user, require_roles
from app.models.appointment import Appointment
from app.models.audit import AuditEvent
from app.models.practitioner import Practitioner
from app.models.user import User
from app.schemas.admin import SuspendRequest
from app.services.audit_service import log_audit_event

router = APIRouter()


@router.get("/users", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT))])
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
    search: str | None = None,
) -> Any:
    """Get users (Admin/Support only)."""
    query = select(User)
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))
    result = await db.execute(query.order_by(User.created_at.desc()).limit(100))
    users = result.scalars().all()
    return [
        {"id": str(u.id), "email": u.email, "role": u.role, "is_active": u.is_active} for u in users
    ]


@router.get(
    "/appointments", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT))]
)
async def get_appointments(
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
    start_date: date | None = None,
    end_date: date | None = None,
) -> Any:
    """Get appointments with date filters."""
    if start_date and end_date and end_date < start_date:
        raise AppError("INVALID_DATE_RANGE", "End date must be on or after start date.")
    query = select(Appointment).where(Appointment.is_deleted.is_(False))
    if start_date:
        query = query.where(
            Appointment.scheduled_start >= datetime.combine(start_date, datetime.min.time(), UTC)
        )
    if end_date:
        query = query.where(
            Appointment.scheduled_start <= datetime.combine(end_date, datetime.max.time(), UTC)
        )
    result = await db.execute(query.order_by(Appointment.scheduled_start.desc()).limit(100))
    appointments = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "patient_id": str(a.patient_id),
            "practitioner_id": str(a.practitioner_id),
            "status": a.status,
            "scheduled_start": a.scheduled_start.isoformat(),
            "scheduled_end": a.scheduled_end.isoformat(),
            "visit_type": a.visit_type,
        }
        for a in appointments
    ]


@router.get(
    "/audit-events", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT))]
)
async def get_audit_events(
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
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
            "details": e.metadata_json,
        }
        for e in events
    ]


@router.get(
    "/integrations/health", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT))]
)
async def check_integrations_health(
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Check health of integrations."""
    try:
        await db.execute(select(1))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {"database": db_status, "redis": "not_checked", "s3": "not_checked"}


@router.post("/practitioners/{id}/suspend", dependencies=[Depends(require_roles(UserRole.ADMIN))])
async def suspend_practitioner(
    id: UUID,
    data: SuspendRequest,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Suspend a practitioner."""
    stmt = (
        update(Practitioner)
        .where(Practitioner.id == id, Practitioner.is_deleted.is_(False))
        .values(status="suspended")
        .returning(Practitioner)
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile:
        await db.flush()
        await log_audit_event(
            db,
            actor_id=current_user.id,
            actor_role=current_user.role,
            action="practitioner.suspended",
            resource_type="practitioner",
            resource_id=profile.id,
            metadata={"reason": data.reason},
        )
        return {
            "id": str(profile.id),
            "user_id": str(profile.user_id),
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "status": profile.status,
        }
    raise NotFoundError("practitioner")
