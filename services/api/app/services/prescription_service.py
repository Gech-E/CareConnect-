"""Prescription and fulfillment service.

Implements SRS §4.10: prescription display, fulfillment choice,
state machine, and controlled substance exclusion.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)

# Fulfillment state machine (SRS §5.3)
FULFILLMENT_TRANSITIONS: dict[str, set[str]] = {
    "not_requested": {"requested"},
    "requested": {"accepted", "failed", "cancelled"},
    "accepted": {"processing", "failed", "cancelled"},
    "processing": {"ready", "dispatched", "failed", "cancelled"},
    "ready": {"completed"},
    "dispatched": {"completed"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


async def get_patient_prescriptions(
    db: AsyncSession,
    patient_id: UUID,
    status_filter: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> dict:
    """List prescriptions for a patient (RX-001)."""
    from app.models.prescription import Prescription

    stmt = select(Prescription).where(
        Prescription.patient_id == patient_id,
        Prescription.is_deleted == False,  # noqa: E712
    )

    if status_filter:
        stmt = stmt.where(Prescription.status == status_filter)

    stmt = stmt.order_by(Prescription.prescribed_at.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    prescriptions = result.scalars().all()

    has_more = len(prescriptions) > limit
    if has_more:
        prescriptions = prescriptions[:limit]

    return {
        "items": [_prescription_to_dict(p) for p in prescriptions],
        "next_cursor": str(prescriptions[-1].id) if has_more else None,
        "has_more": has_more,
    }


async def get_prescription_by_id(
    db: AsyncSession,
    prescription_id: UUID,
    patient_id: UUID,
    ip_address: str | None = None,
) -> dict:
    """Get prescription detail with audit (RX-002)."""
    from app.models.prescription import Prescription

    result = await db.execute(
        select(Prescription).where(Prescription.id == prescription_id)
    )
    rx = result.scalar_one_or_none()
    if not rx:
        raise NotFoundError("prescription")

    if rx.patient_id != patient_id:
        raise ForbiddenError()

    await log_audit_event(
        db,
        actor_id=patient_id,
        actor_role="patient",
        action="prescription.viewed",
        resource_type="prescription",
        resource_id=prescription_id,
        ip_address=ip_address,
    )

    return _prescription_to_dict(rx)


async def get_fulfillment_options(
    db: AsyncSession,
    prescription_id: UUID,
    patient_id: UUID,
) -> list[dict]:
    """Get available fulfillment options (RX-005).

    In production, this would query a pharmacy integration.
    For now, returns mock options.
    """
    from app.models.prescription import Prescription

    result = await db.execute(
        select(Prescription).where(Prescription.id == prescription_id)
    )
    rx = result.scalar_one_or_none()
    if not rx:
        raise NotFoundError("prescription")
    if rx.patient_id != patient_id:
        raise ForbiddenError()

    # RX-008: Exclude controlled substances
    if rx.is_controlled:
        raise AppError(
            code="CONTROLLED_SUBSTANCE_EXCLUDED",
            message="Controlled substance prescriptions are not supported in this version.",
            status_code=400,
        )

    # Mock pharmacy options (adapter would provide real data)
    return [
        {
            "pharmacy_name": "CareConnect Pharmacy - Downtown",
            "pharmacy_address": "123 Health St, Suite 100",
            "delivery_methods": ["pickup"],
            "estimated_time": "Ready in 2-4 hours",
        },
        {
            "pharmacy_name": "CareConnect Home Delivery",
            "pharmacy_address": "Delivered to your address",
            "delivery_methods": ["delivery"],
            "estimated_time": "1-3 business days",
        },
    ]


async def create_fulfillment_request(
    db: AsyncSession,
    *,
    prescription_id: UUID,
    patient_id: UUID,
    pharmacy_name: str,
    delivery_method: str,
    ip_address: str | None = None,
) -> dict:
    """Submit a fulfillment request (RX-005, RX-006, RX-007)."""
    from app.models.prescription import FulfillmentRequest, Prescription

    result = await db.execute(
        select(Prescription).where(Prescription.id == prescription_id)
    )
    rx = result.scalar_one_or_none()
    if not rx:
        raise NotFoundError("prescription")
    if rx.patient_id != patient_id:
        raise ForbiddenError()

    # RX-008: Exclude controlled substances
    if rx.is_controlled:
        raise AppError(
            code="CONTROLLED_SUBSTANCE_EXCLUDED",
            message="Controlled substance prescriptions are not supported.",
            status_code=400,
        )

    # Check for existing active fulfillment request
    existing = await db.execute(
        select(FulfillmentRequest).where(
            FulfillmentRequest.prescription_id == prescription_id,
            FulfillmentRequest.status.in_(["requested", "accepted", "processing"]),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            code="FULFILLMENT_IN_PROGRESS",
            message="A fulfillment request is already in progress for this prescription.",
        )

    fulfillment = FulfillmentRequest(
        prescription_id=prescription_id,
        pharmacy_name=pharmacy_name,
        delivery_method=delivery_method,
        status="requested",
        requested_at=datetime.now(UTC),
    )
    db.add(fulfillment)
    await db.flush()

    # RX-006: Fulfillment status stored separately
    await log_audit_event(
        db,
        actor_id=patient_id,
        actor_role="patient",
        action="fulfillment.requested",
        resource_type="fulfillment_request",
        resource_id=fulfillment.id,
        ip_address=ip_address,
    )

    return {
        "id": str(fulfillment.id),
        "prescription_id": str(prescription_id),
        "pharmacy_name": fulfillment.pharmacy_name,
        "delivery_method": fulfillment.delivery_method,
        "status": fulfillment.status,
        "requested_at": fulfillment.requested_at.isoformat(),
    }


def _prescription_to_dict(rx) -> dict:
    """Convert prescription ORM to dict (RX-002)."""
    return {
        "id": str(rx.id),
        "patient_id": str(rx.patient_id),
        "prescriber_id": str(rx.prescriber_id),
        "medication_name": rx.medication_name,
        "strength": rx.strength,
        "form": rx.form,
        "quantity": rx.quantity,
        "instructions": rx.instructions,
        "refills_total": rx.refills_total,
        "refills_remaining": rx.refills_remaining,
        "status": rx.status,
        "prescribed_at": rx.prescribed_at.isoformat() if rx.prescribed_at else None,
        "expires_at": rx.expires_at.isoformat() if rx.expires_at else None,
        "is_controlled": rx.is_controlled,
    }
