"""Background maintenance and explicit development-only integration stubs."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import structlog
from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import get_settings
from app.models import register_models

settings = get_settings()
register_models()
logger = structlog.get_logger(__name__)
celery_app = Celery(
    "careconnect_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    task_ignore_result=True,
    task_soft_time_limit=120,
    task_time_limit=150,
    broker_connection_retry_on_startup=True,
)


def _require_demo_provider() -> None:
    if not settings.ENABLE_DEMO_PROVIDERS:
        raise NotImplementedError("A real delivery or FHIR adapter must be configured")


@celery_app.task(queue="notifications")
def send_notification_task(notification_id: str, channel: str, payload: dict) -> dict:
    """Simulation only: never claim a message was actually delivered."""
    _require_demo_provider()
    UUID(notification_id)
    return {"status": "simulated", "notification_id": notification_id, "channel": channel}


@celery_app.task(queue="reminders")
def send_appointment_reminder_task(appointment_id: str) -> dict:
    _require_demo_provider()
    UUID(appointment_id)
    return {"status": "simulated", "appointment_id": appointment_id}


@celery_app.task(queue="fhir_sync")
def sync_fhir_records_task(patient_id: str) -> dict:
    _require_demo_provider()
    UUID(patient_id)
    return {"status": "simulated", "patient_id": patient_id}


async def expire_appointment_holds() -> int:
    """Release expired holds with history in one transaction; safe for duplicate jobs."""
    # Celery invokes asyncio.run per task. A pool must not cross event-loop boundaries.
    from app.models.appointment import Appointment, AppointmentStatusHistory

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory.begin() as db:
            now = datetime.now(UTC)
            result = await db.execute(
                select(Appointment)
                .where(Appointment.status == "held", Appointment.hold_expires_at <= now)
                .order_by(Appointment.hold_expires_at)
                .limit(500)
                .with_for_update(skip_locked=True)
            )
            holds = result.scalars().all()
            for hold in holds:
                hold.status = "expired"
                db.add(
                    AppointmentStatusHistory(
                        appointment_id=hold.id,
                        from_status="held",
                        to_status="expired",
                        changed_at=now,
                        reason="Temporary hold expired",
                    )
                )
            return len(holds)
    finally:
        await engine.dispose()


@celery_app.task(
    queue="default", autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=3
)
def expire_appointment_holds_task() -> dict:
    count = asyncio.run(expire_appointment_holds())
    logger.info("maintenance.holds_expired", count=count)
    return {"expired": count}


celery_app.conf.beat_schedule = {
    "expire-holds-every-minute": {
        "task": "app.worker.expire_appointment_holds_task",
        "schedule": 60.0,
    },
}
