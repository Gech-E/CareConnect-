"""Clinician portal endpoints.

Provides appointment management, availability rules, encounter
documents, and prescription creation for clinicians.
"""

from datetime import UTC, datetime, time
from typing import Annotated, Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.core.security import UserRole, get_current_active_user, require_roles
from app.models.appointment import Appointment, AppointmentStatus
from app.models.availability import AvailabilityRule
from app.models.prescription import Prescription
from app.services import appointment_service, record_service
from app.services.access_service import (
    get_active_practitioner,
    get_authorized_appointment,
    get_authorized_encounter,
)
from app.services.audit_service import log_audit_event

# ── Local schemas (clinician-specific) ───────────────────────────────


class AvailabilityRuleInput(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time
    visit_duration_minutes: int = Field(30, ge=10, le=120)
    buffer_minutes: int = Field(10, ge=0, le=60)
    timezone: str = Field("UTC", max_length=50)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Use a valid IANA timezone") from exc
        return value

    @model_validator(mode="after")
    def valid_hours(self):
        if self.start_time.tzinfo or self.end_time.tzinfo or self.end_time <= self.start_time:
            raise ValueError("Use local times with an end after the start")
        return self


class StatusUpdateInput(BaseModel):
    status: AppointmentStatus
    reason: str | None = Field(None, max_length=255)


class PrescriptionInput(BaseModel):
    patient_id: UUID
    medication_name: str = Field(min_length=1, max_length=255)
    strength: str | None = Field(None, max_length=100)
    form: str | None = Field(None, max_length=100)
    quantity: str | None = Field(None, max_length=100)
    instructions: str | None = Field(None, max_length=5000)
    refills_total: int = Field(0, ge=0, le=12)


class DocumentInput(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)


router = APIRouter(
    dependencies=[Depends(require_roles(UserRole.CLINICIAN))],
)


@router.get("/appointments")
async def get_clinician_appointments(
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
    status_filter: str | None = None,
) -> Any:
    """Get the clinician's appointment queue."""
    practitioner = await get_active_practitioner(db, current_user.id)

    stmt = select(Appointment).where(
        Appointment.practitioner_id == practitioner.id,
        Appointment.is_deleted == False,  # noqa: E712
    )
    if status_filter:
        stmt = stmt.where(Appointment.status == status_filter)

    stmt = stmt.order_by(Appointment.scheduled_start.asc()).limit(100)
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
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Get appointment detail for the clinician."""
    return await appointment_service.get_appointment_by_id(
        db, appointment_id, current_user.id, current_user.role
    )


@router.post("/availability", status_code=status.HTTP_201_CREATED)
async def set_availability(
    data: AvailabilityRuleInput,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Create or update availability rules."""
    practitioner = await get_active_practitioner(db, current_user.id)

    rule = AvailabilityRule(
        practitioner_id=practitioner.id,
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
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
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Update an appointment's status (clinician action)."""
    appointment = await get_authorized_appointment(
        db, appointment_id, current_user.id, current_user.role, for_update=True
    )
    if data.status not in {
        "waiting",
        "in_progress",
        "completed",
        "no_show",
        "cancelled_by_clinician",
    }:
        raise ForbiddenError("Use the dedicated booking workflow for this action.")
    appointment_service.validate_transition(appointment.status, data.status)

    old_status = appointment.status
    appointment.status = data.status
    await appointment_service._record_status_change(
        db, appointment.id, old_status, data.status, current_user.id, data.reason
    )
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
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Create a document upload intent for an encounter."""
    ip_address = request.client.host if request.client else None
    return await record_service.create_upload_intent(
        db,
        owner_id=current_user.id,
        owner_role=current_user.role,
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
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Create a prescription from an encounter."""
    practitioner = await get_active_practitioner(db, current_user.id)
    encounter, appointment = await get_authorized_encounter(
        db, encounter_id, current_user.id, current_user.role
    )
    if appointment.patient_id != data.patient_id:
        raise ForbiddenError()
    if encounter.status not in {"in_progress", "completed"}:
        from app.core.exceptions import ConflictError

        raise ConflictError(
            "ENCOUNTER_NOT_READY", "The encounter must have started before prescribing."
        )

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

    return {
        "id": str(prescription.id),
        "medication_name": prescription.medication_name,
        "status": "active",
    }
