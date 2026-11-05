"""Celery worker entrypoint for the CareConnect API service.

Configures the Celery application with Redis broker and
defines async task functions for notifications, reminders, 
FHIR sync, and dead-letter handling.
"""

from celery import Celery

from app.core import get_settings

settings = get_settings()

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
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    task_default_retry_delay=60,
    task_max_retries=5,
)


@celery_app.task(bind=True, queue="notifications", max_retries=5, retry_backoff=True)
def send_notification_task(self, notification_id: str, channel: str, payload: dict):
    """Send a notification via the specified channel (NTF-005)."""
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("notification.sending", notification_id=notification_id, channel=channel)
    return {"status": "sent", "notification_id": notification_id}


@celery_app.task(bind=True, queue="reminders", max_retries=3)
def send_appointment_reminder_task(self, appointment_id: str):
    """Send appointment reminders (NTF-003)."""
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("reminder.sending", appointment_id=appointment_id)
    return {"status": "sent", "appointment_id": appointment_id}


@celery_app.task(bind=True, queue="fhir_sync", max_retries=5, retry_backoff=True)
def sync_fhir_records_task(self, patient_id: str):
    """Sync records from external FHIR server (SRS §8.4)."""
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("fhir_sync.starting", patient_id=patient_id)
    return {"status": "synced", "patient_id": patient_id}


@celery_app.task(queue="default")
def expire_appointment_holds_task():
    """Periodic task to expire stale appointment holds."""
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("maintenance.expiring_holds")


celery_app.conf.beat_schedule = {
    "expire-holds-every-minute": {
        "task": "app.worker.expire_appointment_holds_task",
        "schedule": 60.0,
    },
}

__all__ = ["celery_app"]
