"""Clinician portal endpoints.

Provides appointment management, availability rules, encounter
documents, and prescription creation for clinicians.
"""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import UserRole, get_current_active_user, require_roles
from app.models.appointment import Appointment
from app.models.availability import AvailabilityRule
from app.models.prescription import Prescription
from app.services import appointment_service, record_service
from app.services.audit_service import log_audit_event


# ── Local schemas (clinician-specific) ───────────────────────────────

class AvailabilityRuleInput(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: str = Field(..., description="HH:MM format")
    end_time: str = Field(..., description="HH:MM format")
    visit_duration_minutes: int = Field(30, ge=10, le=120)
    buffer_minutes: int = Field(10, ge=0, le=60)
    timezone: str = Field("America/Los_Angeles")


class StatusUpdateInput(BaseModel):
    status: str = Field(..., description="New appointment status")
    reason: str | None = None


class PrescriptionInput(BaseModel):
    patient_id: UUID
    medication_name: str
    strength: str | None = None
    form: str | None = None
    quantity: str | None = None
    instructions: str | None = None
    refills_total: int = 0


class DocumentInput(BaseModel):
    filename: str
    content_type: str


router = APIRouter(
    dependencies=[Depends(require_roles(UserRole.CLINICIAN))],
)


@router.get("/appointments")
async def get_clinician_appointments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
    status_filter: str | None = None,
) -> Any:
    """Get the clinician's appointment queue."""
    from app.models.practitioner import Practitioner

    # Find practitioner record for this user
    prac_result = await db.execute(
        select(Practitioner).where(Practitioner.user_id == current_user.id)
    )
    practitioner = prac_result.scalar_one_or_none()
    if not practitioner:
        return {"items": []}

    stmt = select(Appointment).where(
        Appointment.practitioner_id == practitioner.id,
        Appointment.is_deleted == False,  # noqa: E712
    )
    if status_filter:
        stmt = stmt.where(Appointment.status == status_filter)

    stmt = stmt.order_by(Appointment.scheduled_start.asc())
    result = await db.execute(stmt)
    appointments = result.scalars().all()

    return {
        "items": [
            {
                "id": str(a.id),
                "patient_id": str(a.patient_id),
                "status": a.status,
                "visit_type": a.visit_type,
                "scheduled_start": a.scheduled_start.isoformat() if a.scheduled_start else None,
                "scheduled_end": a.scheduled_end.isoformat() if a.scheduled_end else None,
            }
            for a in appointments
        ]
    }


@router.get("/appointments/{appointment_id}")
async def get_clinician_appointment_detail(
    appointment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Get appointment detail for the clinician."""
    return await appointment_service.get_appointment_by_id(
        db, appointment_id, current_user.id, current_user.role
    )


@router.post("/availability", status_code=status.HTTP_201_CREATED)
async def set_availability(
    data: AvailabilityRuleInput,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Create or update availability rules."""
    from app.models.practitioner import Practitioner

    prac_result = await db.execute(
        select(Practitioner).where(Practitioner.user_id == current_user.id)
    )
    practitioner = prac_result.scalar_one_or_none()
    if not practitioner:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("practitioner")

    from datetime import time as dt_time
    parts_start = data.start_time.split(":")
    parts_end = data.end_time.split(":")

    rule = AvailabilityRule(
        practitioner_id=practitioner.id,
        day_of_week=data.day_of_week,
        start_time=dt_time(int(parts_start[0]), int(parts_start[1])),
        end_time=dt_time(int(parts_end[0]), int(parts_end[1])),
        visit_duration_minutes=data.visit_duration_minutes,
        buffer_minutes=data.buffer_minutes,
        timezone=data.timezone,
        is_active=True,
    )
    db.add(rule)
    await db.flush()

    return {"id": str(rule.id), "status": "created"}


@router.patch("/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: UUID,
    data: StatusUpdateInput,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Update an appointment's status (clinician action)."""
    from app.models.practitioner import Practitioner

    prac_result = await db.execute(
        select(Practitioner).where(Practitioner.user_id == current_user.id)
    )
    practitioner = prac_result.scalar_one_or_none()

    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("appointment")

    if practitioner and appointment.practitioner_id != practitioner.id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError()

    old_status = appointment.status
    appointment.status = data.status
    await db.flush()

    ip_address = request.client.host if request.client else None
    await log_audit_event(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="appointment.status_updated",
        resource_type="appointment",
        resource_id=appointment_id,
        ip_address=ip_address,
        metadata={"from": old_status, "to": data.status, "reason": data.reason},
    )

    return {"id": str(appointment.id), "status": appointment.status}


@router.post("/encounters/{encounter_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_encounter_document(
    encounter_id: UUID,
    data: DocumentInput,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Create a document upload intent for an encounter."""
    ip_address = request.client.host if request.client else None
    return await record_service.create_upload_intent(
        db,
        owner_id=current_user.id,
        filename=data.filename,
        content_type=data.content_type,
        context_type="encounter",
        context_id=encounter_id,
        ip_address=ip_address,
    )


@router.post("/encounters/{encounter_id}/prescriptions", status_code=status.HTTP_201_CREATED)
async def create_prescription(
    encounter_id: UUID,
    data: PrescriptionInput,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Create a prescription from an encounter."""
    from app.models.practitioner import Practitioner

    prac_result = await db.execute(
        select(Practitioner).where(Practitioner.user_id == current_user.id)
    )
    practitioner = prac_result.scalar_one_or_none()
    if not practitioner:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("practitioner")

    prescription = Prescription(
        patient_id=data.patient_id,
        prescriber_id=practitioner.id,
        encounter_id=encounter_id,
        medication_name=data.medication_name,
        strength=data.strength,
        form=data.form,
        quantity=data.quantity,
        instructions=data.instructions,
        refills_total=data.refills_total,
        refills_remaining=data.refills_total,
        status="active",
        prescribed_at=datetime.now(UTC),
        is_controlled=False,
        source_system="careconnect",
    )
    db.add(prescription)
    await db.flush()

    ip_address = request.client.host if request.client else None
    await log_audit_event(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="prescription.created",
        resource_type="prescription",
        resource_id=prescription.id,
        ip_address=ip_address,
    )

    return {"id": str(prescription.id), "medication_name": prescription.medication_name, "status": "active"}
