"""Regression tests for cross-patient access and unsafe workflow transitions."""

from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppError, ConflictError, ForbiddenError
from app.models import register_models
from app.schemas.appointment import AppointmentHoldRequest
from app.schemas.user import PatientProfileUpdate
from app.services import (
    access_service,
    appointment_service,
    discovery_service,
    record_service,
    video_service,
)

register_models()


def scalar_result(value):
    result = Mock()
    result.scalar_one_or_none.return_value = value
    result.scalar_one.return_value = value
    result.scalars.return_value.all.return_value = value if isinstance(value, list) else [value]
    return result


def database(*results):
    return SimpleNamespace(execute=AsyncMock(side_effect=results), flush=AsyncMock(), add=Mock())


@pytest.mark.asyncio
async def test_clinician_access_resolves_practitioner_profile():
    user_id, practitioner_id = uuid4(), uuid4()
    appointment = SimpleNamespace(patient_id=uuid4(), practitioner_id=practitioner_id)
    db = database(scalar_result(SimpleNamespace(id=practitioner_id)))
    await access_service.authorize_appointment(db, appointment, user_id, "clinician")


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["support", "admin", "clinical_staff", "unknown"])
async def test_unassigned_roles_cannot_read_clinical_appointment(role):
    with pytest.raises(ForbiddenError):
        await access_service.authorize_appointment(
            database(), SimpleNamespace(patient_id=uuid4()), uuid4(), role
        )


@pytest.mark.asyncio
async def test_missing_practitioner_does_not_bypass_authorization():
    with pytest.raises(ForbiddenError):
        await access_service.authorize_appointment(
            database(scalar_result(None)),
            SimpleNamespace(patient_id=uuid4(), practitioner_id=uuid4()),
            uuid4(),
            "clinician",
        )


@pytest.mark.asyncio
async def test_patient_cannot_read_another_patients_appointment():
    with pytest.raises(ForbiddenError):
        await access_service.authorize_appointment(
            database(), SimpleNamespace(patient_id=uuid4()), uuid4(), "patient"
        )


@pytest.mark.asyncio
async def test_idempotency_key_cannot_disclose_another_patients_hold(monkeypatch):
    hold = SimpleNamespace(patient_id=uuid4(), practitioner_id=uuid4())
    db = database(scalar_result(hold))
    monkeypatch.setattr(appointment_service, "_lock_practitioner", AsyncMock())
    with pytest.raises(ConflictError, match="idempotency"):
        await appointment_service.create_slot_hold(
            db,
            patient_id=uuid4(),
            practitioner_id=uuid4(),
            slot_start=datetime.now(UTC) + timedelta(days=1),
            visit_type="video",
            idempotency_key="synthetic-key-1234",
        )
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_check_in_requires_both_confirmations():
    appointment = SimpleNamespace(status="confirmed")
    with pytest.raises(ConflictError) as error:
        await appointment_service.check_in(
            database(scalar_result(appointment)),
            appointment_id=uuid4(),
            patient_id=uuid4(),
            location_confirmed=True,
            emergency_contact_confirmed=False,
        )
    assert error.value.code == "EMERGENCY_CONTACT_NOT_CONFIRMED"
    assert appointment.status == "confirmed"


@pytest.mark.asyncio
async def test_patient_cannot_complete_a_visit():
    with pytest.raises(ForbiddenError):
        await video_service.end_visit(
            database(), appointment_id=uuid4(), user_id=uuid4(), user_role="patient"
        )


@pytest.mark.asyncio
async def test_video_event_authorizes_before_mutating_session(monkeypatch):
    authorize = AsyncMock(side_effect=ForbiddenError())
    monkeypatch.setattr(video_service, "get_authorized_appointment", authorize)
    db = database()
    with pytest.raises(ForbiddenError):
        await video_service.record_video_event(
            db,
            appointment_id=uuid4(),
            user_id=uuid4(),
            user_role="patient",
            event_data={"event_type": "leave"},
        )
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_mock_video_is_unavailable_without_explicit_demo_setting(monkeypatch):
    monkeypatch.setattr(
        video_service,
        "get_authorized_appointment",
        AsyncMock(return_value=SimpleNamespace(status="checked_in")),
    )
    monkeypatch.setattr(
        video_service, "get_settings", lambda: SimpleNamespace(ENABLE_DEMO_PROVIDERS=False)
    )
    with pytest.raises(AppError) as error:
        await video_service.create_video_token(
            database(), appointment_id=uuid4(), user_id=uuid4(), user_role="patient"
        )
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_client_upload_completion_never_marks_content_clean(monkeypatch):
    from app.core import storage

    document = SimpleNamespace(
        id=uuid4(), uploaded_at=None, storage_key="private/key", mime_type="application/pdf"
    )
    monkeypatch.setattr(storage, "inspect_uploaded_object", AsyncMock(return_value=42))
    result = await record_service.complete_upload(
        database(scalar_result(document)), document.id, uuid4(), "a" * 64
    )
    assert result["scan_status"] == "pending"
    assert document.size_bytes == 42


@pytest.mark.asyncio
async def test_unscanned_document_cannot_be_downloaded(monkeypatch):
    document = SimpleNamespace(
        context_type="profile",
        context_id=uuid4(),
        scan_status="pending",
        uploaded_at=datetime.now(UTC),
    )
    signer = Mock()
    monkeypatch.setattr(record_service, "generate_presigned_download_url", signer)
    with pytest.raises(AppError) as error:
        await record_service.get_download_url(
            database(scalar_result(document)), uuid4(), document.context_id, "patient"
        )
    assert error.value.code == "DOCUMENT_UNAVAILABLE"
    signer.assert_not_called()


@pytest.mark.asyncio
async def test_clinician_cannot_download_arbitrary_profile_document():
    document = SimpleNamespace(context_type="profile", context_id=uuid4(), scan_status="clean")
    with pytest.raises(ForbiddenError):
        await record_service.get_download_url(
            database(scalar_result(document)), uuid4(), uuid4(), "clinician"
        )


@pytest.mark.asyncio
async def test_availability_respects_practitioner_timezone():
    day = datetime.now(UTC).date() + timedelta(days=7)
    rule = SimpleNamespace(
        day_of_week=day.weekday(),
        start_time=time(9),
        end_time=time(10),
        visit_duration_minutes=30,
        buffer_minutes=0,
        timezone="Africa/Nairobi",
    )
    result = await discovery_service.get_practitioner_availability(
        database(scalar_result([rule]), scalar_result([]), scalar_result([])), uuid4(), day, day
    )
    slots = result["availability"][day.isoformat()]
    assert datetime.fromisoformat(slots[0]["start"]).astimezone(UTC).hour == 6
    assert len(slots) == 2


def test_booking_rejects_naive_datetime():
    with pytest.raises(ValidationError):
        AppointmentHoldRequest(
            practitioner_id=uuid4(),
            slot_start="2030-01-01T09:00:00",
            visit_type="video",
            idempotency_key="synthetic-key-1234",
        )


def test_profile_names_match_database_columns():
    data = PatientProfileUpdate(first_name="Alice", last_name="Example", date_of_birth="1990-01-01")
    assert data.model_dump()["legal_first_name"] == "Alice"
    assert "first_name" not in data.model_dump()


def test_completed_appointments_cannot_be_reopened():
    with pytest.raises(ConflictError):
        appointment_service.validate_transition("completed", "in_progress")


@pytest.mark.asyncio
async def test_audit_storage_failure_cannot_silently_succeed():
    from app.services.audit_service import log_audit_event

    db = database()
    db.flush.side_effect = RuntimeError("audit storage unavailable")
    with pytest.raises(RuntimeError, match="audit storage unavailable"):
        await log_audit_event(
            db,
            actor_id=uuid4(),
            actor_role="patient",
            action="record.viewed",
            resource_type="medical_record",
            resource_id=uuid4(),
        )
