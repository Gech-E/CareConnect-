"""Consent management service.

Handles accepting and withdrawing consents per patient.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)


async def get_patient_consents(db: AsyncSession, patient_id: UUID) -> list[dict]:
    """List consents for patient."""
    from app.models.consent import Consent

    result = await db.execute(
        select(Consent).where(Consent.patient_id == patient_id)
    )
    consents = result.scalars().all()
    
    return [
        {
            "id": str(c.id),
            "patient_id": str(c.patient_id),
            "consent_type": c.consent_type,
            "version": c.version,
            "status": c.status,
            "accepted_at": c.accepted_at.isoformat() if c.accepted_at else None,
            "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
            "ip_address": c.ip_address,
        }
        for c in consents
    ]


async def accept_consent(
    db: AsyncSession, 
    patient_id: UUID, 
    consent_type: str, 
    version: str, 
    ip_address: str | None = None
) -> dict:
    """Create new consent record, audit log."""
    from app.models.consent import Consent, ConsentStatus

    consent = Consent(
        patient_id=patient_id,
        consent_type=consent_type,
        version=version,
        status=ConsentStatus.accepted,
        accepted_at=datetime.now(UTC),
        ip_address=ip_address,
    )
    db.add(consent)
    await db.flush()

    await log_audit_event(
        db,
        actor_id=patient_id,
        actor_role="patient",
        action="consent.accepted",
        resource_type="consent",
        resource_id=consent.id,
        ip_address=ip_address,
        metadata={"consent_type": consent_type, "version": version}
    )

    return {
        "id": str(consent.id),
        "patient_id": str(consent.patient_id),
        "consent_type": consent.consent_type,
        "version": consent.version,
        "status": consent.status,
        "accepted_at": consent.accepted_at.isoformat(),
        "ip_address": consent.ip_address,
    }


async def withdraw_consent(
    db: AsyncSession, 
    patient_id: UUID, 
    consent_id: UUID, 
    ip_address: str | None = None
) -> dict:
    """Withdraw consent, audit log."""
    from app.models.consent import Consent, ConsentStatus

    result = await db.execute(
        select(Consent).where(Consent.id == consent_id, Consent.patient_id == patient_id)
    )
    consent = result.scalar_one_or_none()
    if not consent:
        raise NotFoundError("consent")

    consent.status = ConsentStatus.withdrawn
    consent.withdrawn_at = datetime.now(UTC)
    await db.flush()

    await log_audit_event(
        db,
        actor_id=patient_id,
        actor_role="patient",
        action="consent.withdrawn",
        resource_type="consent",
        resource_id=consent.id,
        ip_address=ip_address,
    )

    return {
        "id": str(consent.id),
        "status": consent.status,
        "withdrawn_at": consent.withdrawn_at.isoformat(),
    }
