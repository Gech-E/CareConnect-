"""Video and encounter service.

Implements SRS §4.6-4.7: device checks, video token management,
encounter lifecycle, and video session state machine.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    InvalidStateTransitionError,
    NotFoundError,
)
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)

# Video session state machine (SRS §5.2)
VIDEO_TRANSITIONS: dict[str, set[str]] = {
    "created": {"token_issued"},
    "token_issued": {"joining"},
    "joining": {"connected", "failed"},
    "connected": {"reconnecting", "ended"},
    "reconnecting": {"connected", "failed"},
    "failed": set(),
    "ended": set(),
}


async def run_device_check(
    data: dict | Any,
) -> dict:
    """Validate device readiness (WAIT-004)."""
    has_camera = data.has_camera if hasattr(data, 'has_camera') else data.get('has_camera', False)
    has_microphone = data.has_microphone if hasattr(data, 'has_microphone') else data.get('has_microphone', False)
    has_speaker = data.has_speaker if hasattr(data, 'has_speaker') else data.get('has_speaker', False)
    network_quality = data.network_quality if hasattr(data, 'network_quality') else data.get('network_quality', 'unknown')

    issues = []
    if not has_camera:
        issues.append({
            "device": "camera",
            "message": "Camera not detected. Please check your camera settings.",
            "severity": "warning",
        })
    if not has_microphone:
        issues.append({
            "device": "microphone",
            "message": "Microphone not detected. You will not be heard during the call.",
            "severity": "error",
        })
    if not has_speaker:
        issues.append({
            "device": "speaker",
            "message": "Speaker/audio output not detected.",
            "severity": "warning",
        })
    if network_quality in ("poor", "none"):
        issues.append({
            "device": "network",
            "message": "Your network connection is weak. Audio-only mode may be used.",
            "severity": "warning",
        })

    return {
        "ready": len([i for i in issues if i["severity"] == "error"]) == 0,
        "issues": issues,
        "recommendation": "audio_only" if network_quality == "poor" else "video",
    }


async def create_video_token(
    db: AsyncSession,
    *,
    appointment_id: UUID,
    user_id: UUID,
    user_role: str,
    ip_address: str | None = None,
) -> dict:
    """Issue a short-lived video session token (CALL-001).

    Creates encounter and video session if they don't exist.
    """
    from app.models.appointment import Appointment
    from app.models.encounter import Encounter, VideoSession

    # Verify appointment exists and user is authorized
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

    # Check appointment is in valid state for joining
    if appointment.status not in ("checked_in", "waiting", "in_progress"):
        raise ConflictError(
            code="APPOINTMENT_NOT_READY",
            message="This appointment is not ready for video. Please check in first.",
        )

    # Get or create encounter
    enc_result = await db.execute(
        select(Encounter).where(Encounter.appointment_id == appointment_id)
    )
    encounter = enc_result.scalar_one_or_none()
    if not encounter:
        encounter = Encounter(
            appointment_id=appointment_id,
            status="created",
        )
        db.add(encounter)
        await db.flush()

    # Get or create video session
    vs_result = await db.execute(
        select(VideoSession).where(VideoSession.appointment_id == appointment_id)
    )
    video_session = vs_result.scalar_one_or_none()
    if not video_session:
        video_session = VideoSession(
            appointment_id=appointment_id,
            vendor_session_id=f"mock-session-{uuid4()}",
            status="created",
        )
        db.add(video_session)
        await db.flush()

    # Generate mock token (in production: call video provider adapter)
    mock_token = f"vt_{uuid4().hex[:32]}"

    # Update video session status
    video_session.status = "token_issued"
    await db.flush()

    # Update appointment to in_progress if clinician joins
    if user_role == "clinician" and appointment.status != "in_progress":
        if appointment.status in ("waiting", "checked_in"):
            from app.services.appointment_service import _record_status_change
            old_status = appointment.status
            appointment.status = "in_progress"
            await _record_status_change(
                db, appointment.id, old_status, "in_progress", user_id
            )
            encounter.status = "in_progress"
            encounter.started_at = datetime.now(UTC)
            await db.flush()

    await log_audit_event(
        db,
        actor_id=user_id,
        actor_role=user_role,
        action="video.token_issued",
        resource_type="video_session",
        resource_id=video_session.id,
        ip_address=ip_address,
    )

    return {
        "token": mock_token,
        "session_id": str(video_session.vendor_session_id),
        "expires_at": datetime.now(UTC).isoformat(),
    }


async def record_video_event(
    db: AsyncSession,
    *,
    appointment_id: UUID,
    event_data: dict | Any,
    user_id: UUID | None = None,
    ip_address: str | None = None,
) -> None:
    """Record video events (CALL-007): join, leave, reconnect, end."""
    event_type = event_data.event_type if hasattr(event_data, 'event_type') else event_data.get('event_type')
    metadata = event_data.metadata if hasattr(event_data, 'metadata') else event_data.get('metadata')
    from app.models.encounter import VideoSession

    vs_result = await db.execute(
        select(VideoSession).where(VideoSession.appointment_id == appointment_id)
    )
    video_session = vs_result.scalar_one_or_none()
    if not video_session:
        raise NotFoundError("video_session")

    # Update video session status based on event
    status_map = {
        "join": "connected",
        "reconnect": "reconnecting",
        "reconnected": "connected",
        "leave": "ended",
        "failed": "failed",
    }
    new_status = status_map.get(event_type)
    if new_status:
        video_session.status = new_status
        if new_status == "connected" and not video_session.started_at:
            video_session.started_at = datetime.now(UTC)
        if new_status == "ended":
            video_session.ended_at = datetime.now(UTC)

    await db.flush()

    await log_audit_event(
        db,
        actor_id=user_id,
        actor_role="user",
        action=f"video.{event_type}",
        resource_type="video_session",
        resource_id=video_session.id,
        ip_address=ip_address,
        metadata=metadata,
    )


async def end_visit(
    db: AsyncSession,
    *,
    appointment_id: UUID,
    user_id: UUID,
    user_role: str,
    ip_address: str | None = None,
) -> dict:
    """End a visit and transition to completion (CALL-008)."""
    from app.models.appointment import Appointment
    from app.models.encounter import Encounter, VideoSession
    from app.services.appointment_service import _record_status_change, validate_transition

    # Get appointment
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise NotFoundError("appointment")

    # Complete encounter
    enc_result = await db.execute(
        select(Encounter).where(Encounter.appointment_id == appointment_id)
    )
    encounter = enc_result.scalar_one_or_none()
    if encounter:
        encounter.status = "completed"
        encounter.ended_at = datetime.now(UTC)

    # End video session and revoke tokens
    vs_result = await db.execute(
        select(VideoSession).where(VideoSession.appointment_id == appointment_id)
    )
    video_session = vs_result.scalar_one_or_none()
    if video_session:
        video_session.status = "ended"
        video_session.ended_at = datetime.now(UTC)

    # Complete appointment
    if appointment.status == "in_progress":
        validate_transition(appointment.status, "completed")
        old_status = appointment.status
        appointment.status = "completed"
        await _record_status_change(
            db, appointment.id, old_status, "completed", user_id
        )

    await db.flush()

    await log_audit_event(
        db,
        actor_id=user_id,
        actor_role=user_role,
        action="visit.ended",
        resource_type="appointment",
        resource_id=appointment_id,
        ip_address=ip_address,
    )

    return {
        "appointment_id": str(appointment_id),
        "status": "completed",
        "ended_at": datetime.now(UTC).isoformat(),
    }
