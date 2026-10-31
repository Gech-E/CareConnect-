"""Alembic environment configuration for async migrations."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core import get_settings
from app.models import Base

# Import all models so they register with Base.metadata
from app.models.user import User, UserSession  # noqa: F401
from app.models.patient import PatientProfile, InsurancePolicy  # noqa: F401
from app.models.practitioner import Practitioner, PractitionerRole, Organization  # noqa: F401
from app.models.availability import AvailabilityRule, AvailabilityException  # noqa: F401
from app.models.appointment import Appointment, AppointmentStatusHistory  # noqa: F401
from app.models.encounter import Encounter, VideoSession  # noqa: F401
from app.models.consent import Consent  # noqa: F401
from app.models.messaging import MessageThread, MessageThreadParticipant, Message  # noqa: F401
from app.models.record import MedicalRecord, Document  # noqa: F401
from app.models.prescription import Prescription, FulfillmentRequest  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.audit import AuditEvent  # noqa: F401
from app.models.support import SupportCase  # noqa: F401

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
