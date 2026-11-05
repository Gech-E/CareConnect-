"""Real database regression tests. Run only against a dedicated migrated test DB."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import AppError
from app.models import register_models
from app.models.appointment import Appointment
from app.models.practitioner import Practitioner
from app.models.user import User
from app.services.auth_service import refresh_access_token, register_user, revoke_session

pytestmark = pytest.mark.integration
register_models()


@pytest_asyncio.fixture
async def database():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Integration tests require a database name ending in _test")
    engine = create_async_engine(url)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def test_refresh_rotation_rejects_replay_and_logout_revokes(database):
    async with database() as db:
        registration = await register_user(
            db, email=f"{uuid4()}@example.com", password="Synthetic-password-123!"
        )
        original = registration["tokens"].refresh_token
        rotated = await refresh_access_token(db, refresh_token=original)
        with pytest.raises(AppError) as replay:
            await refresh_access_token(db, refresh_token=original)
        assert replay.value.status_code == 401
        await revoke_session(db, UUID(registration["user_id"]))
        with pytest.raises(AppError) as revoked:
            await refresh_access_token(db, refresh_token=rotated["tokens"].refresh_token)
        assert revoked.value.status_code == 401
        # This test deliberately rolls back all synthetic identity data.
        await db.rollback()


async def test_database_prevents_simultaneous_overlapping_bookings(database, monkeypatch):
    patient_id, clinician_id, practitioner_id = uuid4(), uuid4(), uuid4()
    async with database.begin() as db:
        db.add_all(
            [
                User(
                    id=patient_id,
                    email=f"{patient_id}@example.com",
                    password_hash="test",
                    role="patient",
                ),
                User(
                    id=clinician_id,
                    email=f"{clinician_id}@example.com",
                    password_hash="test",
                    role="clinician",
                ),
            ]
        )
        await db.flush()
        db.add(
            Practitioner(
                id=practitioner_id, user_id=clinician_id, first_name="Test", last_name="Clinician"
            )
        )

    start = datetime.now(UTC) + timedelta(days=2)

    async def reserve(offset=0, status="confirmed"):
        try:
            async with database.begin() as db:
                db.add(
                    Appointment(
                        patient_id=patient_id,
                        practitioner_id=practitioner_id,
                        visit_type="video",
                        status=status,
                        scheduled_start=start + timedelta(minutes=offset),
                        scheduled_end=start + timedelta(minutes=offset + 30),
                    )
                )
            return "reserved"
        except IntegrityError:
            return "conflict"

    try:
        assert sorted(await asyncio.gather(reserve(), reserve())) == ["conflict", "reserved"]
        assert await reserve(30) == "reserved"  # Adjacent slots do not overlap.
        assert await reserve(0, "cancelled_by_patient") == "reserved"
        assert await reserve(15) == "conflict"
        # Maintenance releases expired holds and is safe to retry.
        from app import worker

        monkeypatch.setattr(
            worker,
            "settings",
            worker.settings.model_copy(update={"DATABASE_URL": os.environ["TEST_DATABASE_URL"]}),
        )
        async with database.begin() as db:
            db.add(
                Appointment(
                    patient_id=patient_id,
                    practitioner_id=practitioner_id,
                    visit_type="video",
                    status="held",
                    scheduled_start=start + timedelta(minutes=60),
                    scheduled_end=start + timedelta(minutes=90),
                    hold_expires_at=datetime.now(UTC) - timedelta(minutes=1),
                )
            )
        assert await worker.expire_appointment_holds() == 1
        assert await worker.expire_appointment_holds() == 0
        assert await reserve(60) == "reserved"
    finally:
        async with database.begin() as db:
            await db.execute(delete(User).where(User.id.in_([patient_id, clinician_id])))
