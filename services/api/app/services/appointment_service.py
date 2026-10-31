"""Appointment service implementing the SRS §5.1 state machine.

Handles slot holds, booking (idempotent), rescheduling, cancellation,
check-in, and all state transitions with audit logging.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidStateTransitionError,
    NotFoundError,
    SlotUnavailableError,
)
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── State machine transitions (SRS §5.1) ────────────────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"held"},
    "held": {"confirmed", "expired"},
    "confirmed": {"checked_in", "rescheduled", "cancelled_by_patient", "cancelled_by_clinician"},
    "checked_in": {"waiting", "rescheduled", "cancelled_by_patient", "cancelled_by_clinician"},
    "waiting": {"in_progress", "rescheduled", "cancelled_by_patient", "cancelled_by_clinician", "no_show"},
    "in_progress": {"completed"},
    # Terminal states — no further transitions
    "completed": set(),
    "rescheduled": set(),
    "cancelled_by_patient": set(),
    "cancelled_by_clinician": set(),
    "no_show": set(),
    "expired": set(),
}


def validate_transition(from_status: str, to_status: str) -> None:
    """Validate that a state transition is legal per SRS §5.1."""
    allowed = VALID_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise InvalidStateTransitionError("appointment", from_status, to_status)


async def _record_status_change(
    db: AsyncSession,
    appointment_id: UUID,
    from_status: str,
    to_status: str,
    changed_by_id: UUID,
    reason: str | None = None,
) -> None:
    """Record appointment status transition history (SRS §5.1)."""
    from app.models.appointment import AppointmentStatusHistory

    history = AppointmentStatusHistory(
        appointment_id=appointment_id,
        from_status=from_status,
        to_status=to_status,
        changed_by_id=changed_by_id,
        reason=reason,
    )
    db.add(history)


# ── Slot hold ────────────────────────────────────────────────────────

async def create_slot_hold(
    db: AsyncSession,
    *,
    patient_id: UUID,
    practitioner_id: UUID,
    slot_start: datetime,
    visit_type: str,
    idempotency_key: str,
    ip_address: str | None = None,
) -> dict:
    """Create a temporary slot hold (APT-004).

    Prevents double booking during confirmation by using a database
    constraint on (practitioner_id, scheduled_start, status).
    """
    from app.models.appointment import Appointment

    # Check idempotency — return existing hold if key matches
    existing = await db.execute(
        select(Appointment).where(Appointment.idempotency_key == idempotency_key)
    )
    if hold := existing.scalar_one_or_none():
        return {
            "hold_id": str(hold.id),
            "expires_at": hold.hold_expires_at.isoformat() if hold.hold_expires_at else None,
            "status": hold.status,
        }

    # Check for overlapping confirmed appointments
    slot_end = slot_start + timedelta(minutes=settings.DEFAULT_VISIT_DURATION_MINUTES)
    overlap = await db.execute(
        select(Appointment).where(
            Appointment.practitioner_id == practitioner_id,
            Appointment.status.in_(["held", "confirmed", "checked_in", "waiting", "in_progress"]),
            Appointment.scheduled_start < slot_end,
            Appointment.scheduled_end > slot_start,
        )
    )
    if overlap.scalar_one_or_none():
        raise SlotUnavailableError()

    hold_expires = datetime.now(UTC) + timedelta(seconds=settings.SLOT_HOLD_TTL_SECONDS)

    appointment = Appointment(
        patient_id=patient_id,
        practitioner_id=practitioner_id,
        visit_type=visit_type,
        status="held",
        scheduled_start=slot_start,
        scheduled_end=slot_end,
        hold_expires_at=hold_expires,
        idempotency_key=idempotency_key,
    )
    db.add(appointment)
    await db.flush()

    await log_audit_event(
        db,
        actor_id=patient_id,
        actor_role="patient",
        action="appointment.hold_created",
        resource_type="appointment",
        resource_id=appointment.id,
        ip_address=ip_address,
    )

    return {
        "hold_id": str(appointment.id),
        "expires_at": hold_expires.isoformat(),
        "status": "held",
    }


# ── Booking ──────────────────────────────────────────────────────────

async def confirm_appointment(
    db: AsyncSession,
    *,
    hold_id: UUID,
    patient_id: UUID,
    preparation_notes: str | None = None,
    idempotency_key: str | None = None,
    ip_address: str | None = None,
) -> dict:
    """Confirm a held appointment (APT-005 idempotent)."""
    from app.models.appointment import Appointment

    result = await db.execute(
        select(Appointment).where(
            Appointment.id == hold_id,
            Appointment.patient_id == patient_id,
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise NotFoundError("appointment")

    # Idempotency: already confirmed
    if appointment.status == "confirmed":
        return _appointment_to_dict(appointment)

    # Check hold expiry
    if appointment.hold_expires_at and appointment.hold_expires_at < datetime.now(UTC):
        appointment.status = "expired"
        await db.flush()
        raise ConflictError(
            code="HOLD_EXPIRED",
            message="The slot hold has expired. Please select a new time.",
        )

    validate_transition(appointment.status, "confirmed")
    old_status = appointment.status
    appointment.status = "confirmed"
    appointment.preparation_instructions = preparation_notes

    await _record_status_change(
        db, appointment.id, old_status, "confirmed", patient_id
    )
    await db.flush()

    await log_audit_event(
        db,
        actor_id=patient_id,
        actor_role="patient",
        action="appointment.confirmed",
        resource_type="appointment",
        resource_id=appointment.id,
        ip_address=ip_address,
    )

    return _appointment_to_dict(appointment)


# ── Reschedule ───────────────────────────────────────────────────────

async def reschedule_appointment(
    db: AsyncSession,
    *,
    appointment_id: UUID,
    user_id: UUID,
    user_role: str,
    new_slot_start: datetime,
    reason: str | None = None,
    ip_address: str | None = None,
) -> dict:
    """Reschedule an appointment — creates a new one linked to the original."""
    from app.models.appointment import Appointment

    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    original = result.scalar_one_or_none()
    if not original:
        raise NotFoundError("appointment")

    # Authorization check
    if user_role == "patient" and original.patient_id != user_id:
        raise ForbiddenError()
    if user_role == "clinician" and original.practitioner_id != user_id:
        raise ForbiddenError()

    validate_transition(original.status, "rescheduled")
    old_status = original.status
    original.status = "rescheduled"

    await _record_status_change(
        db, original.id, old_status, "rescheduled", user_id, reason
    )

    # Create new appointment linked to original
    new_end = new_slot_start + timedelta(minutes=settings.DEFAULT_VISIT_DURATION_MINUTES)
    new_appointment = Appointment(
        patient_id=original.patient_id,
        practitioner_id=original.practitioner_id,
        organization_id=original.organization_id,
        visit_type=original.visit_type,
        status="confirmed",
        scheduled_start=new_slot_start,
        scheduled_end=new_end,
        rescheduled_from_id=original.id,
        idempotency_key=str(uuid4()),
    )
    db.add(new_appointment)
    await db.flush()

    await log_audit_event(
        db,
        actor_id=user_id,
        actor_role=user_role,
        action="appointment.rescheduled",
        resource_type="appointment",
        resource_id=original.id,
        ip_address=ip_address,
        metadata={"new_appointment_id": str(new_appointment.id), "reason": reason},
    )

    return _appointment_to_dict(new_appointment)


# ── Cancellation ─────────────────────────────────────────────────────

async def cancel_appointment(
    db: AsyncSession,
    *,
    appointment_id: UUID,
    user_id: UUID,
    user_role: str,
    reason: str | None = None,
    ip_address: str | None = None,
) -> dict:
    """Cancel an appointment with proper role-based status."""
    from app.models.appointment import Appointment

    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise NotFoundError("appointment")

    # Determine cancellation status based on role
    if user_role in ("clinician", "clinical_staff"):
        if appointment.practitioner_id != user_id and user_role == "clinician":
            raise ForbiddenError()
        new_status = "cancelled_by_clinician"
    else:
        if appointment.patient_id != user_id:
            raise ForbiddenError()
        new_status = "cancelled_by_patient"

    validate_transition(appointment.status, new_status)
    old_status = appointment.status
    appointment.status = new_status
    appointment.cancellation_reason = reason

    await _record_status_change(
        db, appointment.id, old_status, new_status, user_id, reason
    )
    await db.flush()

    await log_audit_event(
        db,
        actor_id=user_id,
        actor_role=user_role,
        action="appointment.cancelled",
        resource_type="appointment",
        resource_id=appointment.id,
        ip_address=ip_address,
        metadata={"reason": reason},
    )

    return _appointment_to_dict(appointment)


# ── Check-in ─────────────────────────────────────────────────────────

async def check_in(
    db: AsyncSession,
    *,
    appointment_id: UUID,
    patient_id: UUID,
    location_confirmed: bool = True,
    emergency_contact_confirmed: bool = True,
    ip_address: str | None = None,
) -> dict:
    """Patient checks in for an appointment (WAIT-002)."""
    from app.models.appointment import Appointment

    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id,
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise NotFoundError("appointment")

    if not location_confirmed:
        raise ConflictError(
            code="LOCATION_NOT_CONFIRMED",
            message="Please confirm your current physical location before checking in.",
        )

    validate_transition(appointment.status, "checked_in")
    old_status = appointment.status
    appointment.status = "checked_in"

    await _record_status_change(
        db, appointment.id, old_status, "checked_in", patient_id
    )
    await db.flush()

    await log_audit_event(
        db,
        actor_id=patient_id,
        actor_role="patient",
        action="appointment.checked_in",
        resource_type="appointment",
        resource_id=appointment.id,
        ip_address=ip_address,
    )

    return _appointment_to_dict(appointment)


# ── Query ────────────────────────────────────────────────────────────

async def get_patient_appointments(
    db: AsyncSession,
    patient_id: UUID,
    status_filter: str | None = None,
    upcoming_only: bool = False,
    limit: int = 20,
    cursor: str | None = None,
) -> dict:
    """List appointments for a patient with cursor pagination."""
    from app.models.appointment import Appointment

    query = select(Appointment).where(
        Appointment.patient_id == patient_id,
        Appointment.is_deleted == False,  # noqa: E712
    )

    if status_filter:
        query = query.where(Appointment.status == status_filter)
    if upcoming_only:
        query = query.where(Appointment.scheduled_start > datetime.now(UTC))

    query = query.order_by(Appointment.scheduled_start.desc()).limit(limit + 1)

    if cursor:
        from uuid import UUID as UUIDType
        query = query.where(Appointment.id < UUIDType(cursor))

    result = await db.execute(query)
    appointments = result.scalars().all()

    has_more = len(appointments) > limit
    if has_more:
        appointments = appointments[:limit]

    return {
        "items": [_appointment_to_dict(a) for a in appointments],
        "next_cursor": str(appointments[-1].id) if has_more else None,
        "has_more": has_more,
    }


async def get_appointment_by_id(
    db: AsyncSession,
    appointment_id: UUID,
    user_id: UUID,
    user_role: str,
) -> dict:
    """Get a single appointment with authorization check."""
    from app.models.appointment import Appointment

    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise NotFoundError("appointment")

    # Authorization
    if user_role == "patient" and appointment.patient_id != user_id:
        raise ForbiddenError()
    if user_role == "clinician" and appointment.practitioner_id != user_id:
        raise ForbiddenError()

    return _appointment_to_dict(appointment)


def _appointment_to_dict(appointment) -> dict:
    """Convert appointment ORM instance to dictionary."""
    return {
        "id": str(appointment.id),
        "patient_id": str(appointment.patient_id),
        "practitioner_id": str(appointment.practitioner_id),
        "organization_id": str(appointment.organization_id) if appointment.organization_id else None,
        "visit_type": appointment.visit_type,
        "status": appointment.status,
        "scheduled_start": appointment.scheduled_start.isoformat() if appointment.scheduled_start else None,
        "scheduled_end": appointment.scheduled_end.isoformat() if appointment.scheduled_end else None,
        "timezone": appointment.timezone,
        "cancellation_reason": appointment.cancellation_reason,
        "rescheduled_from_id": str(appointment.rescheduled_from_id) if appointment.rescheduled_from_id else None,
        "preparation_instructions": appointment.preparation_instructions,
        "estimated_price": float(appointment.estimated_price) if appointment.estimated_price else None,
        "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
        "updated_at": appointment.updated_at.isoformat() if appointment.updated_at else None,
    }
