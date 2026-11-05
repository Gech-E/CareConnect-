from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import UserRole, get_current_active_user, require_roles
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentCheckInRequest,
    AppointmentConfirmRequest,
    AppointmentHoldRequest,
    AppointmentRescheduleRequest,
)
from app.services import appointment_service

router = APIRouter()


@router.post("/appointment-holds", dependencies=[Depends(require_roles(UserRole.PATIENT))])
async def create_appointment_hold(
    request: Request,
    data: AppointmentHoldRequest,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
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
        ip_address=ip_address,
    )


@router.post("/appointments", dependencies=[Depends(require_roles(UserRole.PATIENT))])
async def confirm_appointment(
    data: AppointmentConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Confirm an appointment."""
    return await appointment_service.confirm_appointment(
        db,
        hold_id=data.hold_id,
        patient_id=current_user.id,
        preparation_notes=data.preparation_notes,
        idempotency_key=data.idempotency_key,
    )


@router.get("/appointments")
async def get_appointments(
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
    status_filter: str | None = None,
) -> Any:
    """Get patient appointments."""
    return await appointment_service.get_patient_appointments(
        db, patient_id=current_user.id, status_filter=status_filter
    )


@router.get("/appointments/{id}")
async def get_appointment(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Get appointment details."""
    return await appointment_service.get_appointment_by_id(
        db, appointment_id=id, user_id=current_user.id, user_role=current_user.role
    )


@router.post("/appointments/{id}/check-in", dependencies=[Depends(require_roles(UserRole.PATIENT))])
async def check_in_appointment(
    id: UUID,
    data: AppointmentCheckInRequest,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Check in for an appointment."""
    return await appointment_service.check_in(
        db,
        appointment_id=id,
        patient_id=current_user.id,
        location_confirmed=data.location_confirmed,
        emergency_contact_confirmed=data.emergency_contact_confirmed,
    )


@router.post("/appointments/{id}/reschedule")
async def reschedule_appointment(
    id: UUID,
    data: AppointmentRescheduleRequest,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Reschedule an appointment."""
    return await appointment_service.reschedule_appointment(
        db,
        appointment_id=id,
        user_id=current_user.id,
        user_role=current_user.role,
        new_slot_start=data.new_slot_start,
        reason=data.reason,
    )


@router.post("/appointments/{id}/cancel")
async def cancel_appointment(
    id: UUID,
    data: AppointmentCancelRequest,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Cancel an appointment."""
    return await appointment_service.cancel_appointment(
        db,
        appointment_id=id,
        user_id=current_user.id,
        user_role=current_user.role,
        reason=data.reason,
    )


@router.post("/appointments/{id}/calendar-export")
async def export_calendar(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Export appointment to iCal format."""
    appointment = await appointment_service.get_appointment_by_id(
        db, id, current_user.id, current_user.role
    )
    from datetime import UTC, datetime

    from icalendar import Calendar, Event

    calendar = Calendar()
    calendar.add("version", "2.0")
    calendar.add("prodid", "-//CareConnect//Appointments//EN")
    event = Event()
    event.add("uid", f"{id}@careconnect")
    event.add("summary", "CareConnect appointment")
    event.add("dtstamp", datetime.now(UTC))
    event.add("dtstart", datetime.fromisoformat(appointment["scheduled_start"]))
    event.add("dtend", datetime.fromisoformat(appointment["scheduled_end"]))
    calendar.add_component(event)
    return Response(
        content=calendar.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="appointment.ics"'},
    )
