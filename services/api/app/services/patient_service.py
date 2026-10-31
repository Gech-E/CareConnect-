"""Patient profile and insurance service.

Handles patient profiles, insurance policies, and account closures.
"""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)


async def get_patient_profile(db: AsyncSession, user_id: UUID) -> dict:
    """Query PatientProfile by user_id."""
    from app.models.patient import PatientProfile

    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise NotFoundError("patient profile")

    return {
        "id": str(profile.id),
        "user_id": str(profile.user_id),
        "legal_first_name": profile.legal_first_name,
        "legal_last_name": profile.legal_last_name,
        "date_of_birth": profile.date_of_birth.isoformat(),
        "gender": profile.gender,
        "address_line1": profile.address_line1,
        "address_line2": profile.address_line2,
        "city": profile.city,
        "state": profile.state,
        "zip_code": profile.zip_code,
        "country": profile.country,
        "timezone": profile.timezone,
        "preferred_language": profile.preferred_language,
        "emergency_contact_name": profile.emergency_contact_name,
        "emergency_contact_phone": profile.emergency_contact_phone,
    }


async def update_patient_profile(db: AsyncSession, user_id: UUID, **updates) -> dict:
    """Update PatientProfile fields, audit log."""
    from app.models.patient import PatientProfile

    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise NotFoundError("patient profile")

    for key, value in updates.items():
        if hasattr(profile, key):
            setattr(profile, key, value)

    await db.flush()

    await log_audit_event(
        db,
        actor_id=user_id,
        actor_role="patient",
        action="patient_profile.updated",
        resource_type="patient_profile",
        resource_id=profile.id,
    )

    return await get_patient_profile(db, user_id)


async def get_insurance_policies(db: AsyncSession, patient_id: UUID) -> list[dict]:
    """List insurance policies."""
    from app.models.patient import InsurancePolicy

    result = await db.execute(
        select(InsurancePolicy).where(InsurancePolicy.patient_id == patient_id)
    )
    policies = result.scalars().all()
    
    return [
        {
            "id": str(policy.id),
            "patient_id": str(policy.patient_id),
            "payer_name": policy.payer_name,
            "member_id": policy.member_id,
            "group_number": policy.group_number,
            "plan_name": policy.plan_name,
            "verification_status": policy.verification_status,
            "verified_at": policy.verified_at.isoformat() if policy.verified_at else None,
            "policy_document_id": str(policy.policy_document_id) if policy.policy_document_id else None,
        }
        for policy in policies
    ]


async def create_insurance_policy(db: AsyncSession, patient_id: UUID, **data) -> dict:
    """Create new policy."""
    from app.models.patient import InsurancePolicy

    policy = InsurancePolicy(
        patient_id=patient_id,
        payer_name=data.get("payer_name"),
        member_id=data.get("member_id"),
        group_number=data.get("group_number"),
        plan_name=data.get("plan_name"),
        policy_document_id=data.get("policy_document_id"),
    )
    db.add(policy)
    await db.flush()

    await log_audit_event(
        db,
        actor_id=patient_id,  # Assume patient is creating their own policy
        actor_role="patient",
        action="insurance_policy.created",
        resource_type="insurance_policy",
        resource_id=policy.id,
    )

    return {
        "id": str(policy.id),
        "patient_id": str(policy.patient_id),
        "payer_name": policy.payer_name,
        "member_id": policy.member_id,
        "group_number": policy.group_number,
        "plan_name": policy.plan_name,
        "verification_status": policy.verification_status,
        "verified_at": policy.verified_at.isoformat() if policy.verified_at else None,
        "policy_document_id": str(policy.policy_document_id) if policy.policy_document_id else None,
    }


async def request_account_closure(db: AsyncSession, user_id: UUID, ip_address: str | None = None) -> dict:
    """Mark user for closure, audit log."""
    from app.models.user import User

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("user")
        
    user.is_active = False
    await db.flush()

    await log_audit_event(
        db,
        actor_id=user_id,
        actor_role=user.role,
        action="account.closure_requested",
        resource_type="user",
        resource_id=user_id,
        ip_address=ip_address,
    )
    
    return {"status": "closure_requested", "user_id": str(user_id)}
