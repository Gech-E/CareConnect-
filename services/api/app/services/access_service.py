"""Resource-level authorization shared by clinical workflows.

Being a clinician is not sufficient to access a patient's records: the
practitioner profile must be active and assigned to the appointment.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.appointment import Appointment
from app.models.encounter import Encounter
from app.models.practitioner import Practitioner


async def get_active_practitioner(db: AsyncSession, user_id: UUID) -> Practitioner:
    result = await db.execute(
        select(Practitioner).where(
            Practitioner.user_id == user_id,
            Practitioner.status == "active",
            Practitioner.is_deleted.is_(False),
        )
    )
    practitioner = result.scalar_one_or_none()
    if practitioner is None:
        raise ForbiddenError()
    return practitioner


async def authorize_appointment(
    db: AsyncSession, appointment: Appointment, user_id: UUID, user_role: str
) -> None:
    if user_role == "patient" and appointment.patient_id == user_id:
        return
    if user_role == "clinician":
        practitioner = await get_active_practitioner(db, user_id)
        if appointment.practitioner_id == practitioner.id:
            return
    raise ForbiddenError()


async def get_authorized_appointment(
    db: AsyncSession,
    appointment_id: UUID,
    user_id: UUID,
    user_role: str,
    *,
    for_update: bool = False,
) -> Appointment:
    query = select(Appointment).where(
        Appointment.id == appointment_id, Appointment.is_deleted.is_(False)
    )
    if for_update:
        query = query.with_for_update().execution_options(populate_existing=True)
    result = await db.execute(query)
    appointment = result.scalar_one_or_none()
    if appointment is None:
        raise NotFoundError("appointment")
    await authorize_appointment(db, appointment, user_id, user_role)
    return appointment


async def get_authorized_encounter(
    db: AsyncSession, encounter_id: UUID, user_id: UUID, user_role: str
) -> tuple[Encounter, Appointment]:
    result = await db.execute(
        select(Encounter).where(Encounter.id == encounter_id, Encounter.is_deleted.is_(False))
    )
    encounter = result.scalar_one_or_none()
    if encounter is None:
        raise NotFoundError("encounter")
    appointment = await get_authorized_appointment(db, encounter.appointment_id, user_id, user_role)
    return encounter, appointment
