"""Patient profile, session, and consent management endpoints."""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.consent import Consent
from app.models.patient import PatientProfile
from app.schemas.consent import ConsentCreateRequest
from app.schemas.user import PatientProfileUpdate
from app.services import auth_service
from app.services.audit_service import log_audit_event

router = APIRouter()


@router.get("/")
async def get_me(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Get current user profile and associated data."""
    response = {
        "id": str(current_user.id),
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
    }
    if current_user.role == "patient":
        result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            response["profile"] = {
                "legal_first_name": profile.legal_first_name,
                "legal_last_name": profile.legal_last_name,
                "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
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
                "communication_pref_email": profile.communication_pref_email,
                "communication_pref_sms": profile.communication_pref_sms,
                "communication_pref_push": profile.communication_pref_push,
            }
    return response


@router.patch("/profile")
async def update_profile(
    data: PatientProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Update the current patient's profile."""
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        # Create profile if it doesn't exist
        profile = PatientProfile(user_id=current_user.id)
        db.add(profile)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)

    await db.flush()
    return {"status": "updated"}


@router.get("/sessions")
async def get_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """List active sessions for the current user."""
    return await auth_service.get_user_sessions(db, current_user.id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> None:
    """Revoke a specific user session."""
    await auth_service.revoke_session(db, current_user.id, session_id)


@router.get("/consents")
async def get_consents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """List consent records for the current user."""
    result = await db.execute(
        select(Consent).where(Consent.patient_id == current_user.id)
        .order_by(Consent.accepted_at.desc())
    )
    consents = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "consent_type": c.consent_type,
            "version": c.version,
            "status": c.status,
            "accepted_at": c.accepted_at.isoformat() if c.accepted_at else None,
            "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
        }
        for c in consents
    ]


@router.post("/consents", status_code=status.HTTP_201_CREATED)
async def create_consent(
    request: Request,
    data: ConsentCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Accept a consent."""
    ip_address = request.client.host if request.client else None
    consent = Consent(
        patient_id=current_user.id,
        consent_type=data.consent_type,
        version=data.version,
        status="accepted",
        accepted_at=datetime.now(UTC),
        ip_address=ip_address,
    )
    db.add(consent)
    await db.flush()

    await log_audit_event(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="consent.accepted",
        resource_type="consent",
        resource_id=consent.id,
        ip_address=ip_address,
    )

    return {
        "id": str(consent.id),
        "consent_type": consent.consent_type,
        "version": consent.version,
        "status": consent.status,
    }


@router.post("/account-closure-requests", status_code=status.HTTP_202_ACCEPTED)
async def request_account_closure(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)],
) -> Any:
    """Request account closure. The request will be reviewed by support."""
    ip_address = request.client.host if request.client else None

    await log_audit_event(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="account.closure_requested",
        resource_type="user",
        resource_id=current_user.id,
        ip_address=ip_address,
    )

    return {
        "status": "closure_requested",
        "message": "Your account closure request has been submitted for review.",
    }
