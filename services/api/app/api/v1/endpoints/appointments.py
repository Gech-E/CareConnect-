from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any, Optional
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services import appointment_service
from app.schemas.appointment import AppointmentHoldRequest, AppointmentConfirmRequest, AppointmentRescheduleRequest, AppointmentCancelRequest, AppointmentCheckInRequest

router = APIRouter()

@router.post("/appointment-holds")
async def create_appointment_hold(
    request: Request,
    data: AppointmentHoldRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Create an appointment hold."""
    ip_address = request.client.host if request.client else None
    return await appointment_service.create_slot_hold(
        db,
        patient_id=current_user.id,
        practitioner_id=data.practitioner_id,
        slot_start=data.slot_start,
        visit_type=data.visit_type,
        idempotency_key=data.idempotency_key,
        ip_address=ip_address
    )

@router.post("/appointments")
async def confirm_appointment(
    data: AppointmentConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Confirm an appointment."""
    return await appointment_service.confirm_appointment(
        db,
        hold_id=data.hold_id,
        patient_id=current_user.id
    )

@router.get("/appointments")
async def get_appointments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
    status_filter: Optional[str] = None
) -> Any:
    """Get patient appointments."""
    return await appointment_service.get_patient_appointments(
        db,
        patient_id=current_user.id,
        status_filter=status_filter
    )

@router.get("/appointments/{id}")
async def get_appointment(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get appointment details."""
    return await appointment_service.get_appointment_by_id(
        db,
        appointment_id=id,
        user_id=current_user.id,
        user_role=current_user.role
    )

@router.post("/appointments/{id}/check-in")
async def check_in_appointment(
    id: UUID,
    data: AppointmentCheckInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Check in for an appointment."""
    return await appointment_service.check_in(
        db,
        appointment_id=id,
        patient_id=current_user.id
    )

@router.post("/appointments/{id}/reschedule")
async def reschedule_appointment(
    id: UUID,
    data: AppointmentRescheduleRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Reschedule an appointment."""
    return await appointment_service.reschedule_appointment(
        db,
        appointment_id=id,
        user_id=current_user.id,
        user_role=current_user.role,
        new_slot_start=data.new_slot_start
    )

@router.post("/appointments/{id}/cancel")
async def cancel_appointment(
    id: UUID,
    data: AppointmentCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Cancel an appointment."""
    return await appointment_service.cancel_appointment(
        db,
        appointment_id=id,
        user_id=current_user.id,
        user_role=current_user.role,
        reason=data.reason
    )

@router.post("/appointments/{id}/calendar-export")
async def export_calendar(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Export appointment to iCal format."""
    appointment = await appointment_service.get_appointment_by_id(db, id, current_user.id, current_user.role)
    ical_content = f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:Appointment\nUID:{id}\nEND:VEVENT\nEND:VCALENDAR"
    return Response(content=ical_content, media_type="text/calendar")
