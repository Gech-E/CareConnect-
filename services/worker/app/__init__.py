"""Celery worker configuration and task definitions.

Provides async background job processing for notifications,
FHIR sync, appointment reminders, and dead-letter handling
per SRS §REL-004, REL-005.
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
    # Dead letter queue handling
    task_default_queue="default",
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "notifications": {"exchange": "notifications", "routing_key": "notifications"},
        "fhir_sync": {"exchange": "fhir_sync", "routing_key": "fhir_sync"},
        "reminders": {"exchange": "reminders", "routing_key": "reminders"},
        "dead_letter": {"exchange": "dead_letter", "routing_key": "dead_letter"},
    },
    # Retry configuration
    task_default_retry_delay=60,
    task_max_retries=5,
)


# ── Notification Tasks ──────────────────────────────────────────────

@celery_app.task(
    bind=True,
    queue="notifications",
    max_retries=5,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def send_notification_task(self, notification_id: str, channel: str, payload: dict):
    """Send a notification via the specified channel.

    Per NTF-005: Retries with bounded backoff.
    Per NTF-002: Payload must not contain PHI.
    """
    import structlog
    logger = structlog.get_logger(__name__)

    try:
        logger.info(
            "notification.sending",
            notification_id=notification_id,
            channel=channel,
        )

        # In production: use the appropriate adapter
        # For now, just log
        logger.info(
            "notification.sent",
            notification_id=notification_id,
            channel=channel,
            status="delivered",
        )

        return {"status": "sent", "notification_id": notification_id}

    except Exception as exc:
        logger.error(
            "notification.failed",
            notification_id=notification_id,
            channel=channel,
            error=str(exc),
        )
        # Move to dead letter after max retries
        if self.request.retries >= self.max_retries:
            move_to_dead_letter.delay(
                task_name="send_notification",
                original_args={"notification_id": notification_id},
                error=str(exc),
            )
        raise


@celery_app.task(
    bind=True,
    queue="reminders",
    max_retries=3,
    default_retry_delay=60,
)
def send_appointment_reminder_task(self, appointment_id: str):
    """Send appointment reminders (NTF-003).

    Generic content only — no PHI in the reminder.
    """
    import structlog
    logger = structlog.get_logger(__name__)

    logger.info(
        "reminder.sending",
        appointment_id=appointment_id,
    )

    # In production: query appointment, get patient notification prefs,
    # compose generic reminder, send via preferred channels
    return {"status": "sent", "appointment_id": appointment_id}


@celery_app.task(
    bind=True,
    queue="fhir_sync",
    max_retries=5,
    default_retry_delay=120,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def sync_fhir_records_task(self, patient_id: str):
    """Sync records from external FHIR server.

    Per SRS §8.4: Use retry and dead-letter queues for transient failures.
    """
    import structlog
    logger = structlog.get_logger(__name__)

    logger.info("fhir_sync.starting", patient_id=patient_id)

    # In production: call FHIR adapter, import records
    return {"status": "synced", "patient_id": patient_id}


@celery_app.task(queue="dead_letter")
def move_to_dead_letter(task_name: str, original_args: dict, error: str):
    """Move failed tasks to dead letter queue for manual review (REL-005)."""
    import structlog
    logger = structlog.get_logger(__name__)

    logger.warning(
        "dead_letter.received",
        task_name=task_name,
        original_args=original_args,
        error=error,
    )
    # In production: alert ops team, store in database for review


@celery_app.task(queue="default")
def expire_appointment_holds_task():
    """Periodic task to expire stale appointment holds."""
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("maintenance.expiring_holds")
    # In production: query and expire holds past TTL


# ── Beat Schedule (periodic tasks) ──────────────────────────────────

celery_app.conf.beat_schedule = {
    "expire-holds-every-minute": {
        "task": "app.worker.expire_appointment_holds_task",
        "schedule": 60.0,
    },
}
