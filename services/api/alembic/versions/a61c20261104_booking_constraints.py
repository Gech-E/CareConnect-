"""Enforce appointment intervals and prevent concurrent double booking.

Revision ID: a61c20261104
Revises: 41843889707a
"""

from alembic import op

revision = "a61c20261104"
down_revision = "41843889707a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Requires extension privileges during migration, not on the runtime DB role.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    # Existing conflicting bookings deliberately fail migration; never discard care data.
    op.create_check_constraint(
        "appointments_positive_duration", "appointments", "scheduled_end > scheduled_start"
    )
    op.execute("""
        ALTER TABLE appointments ADD CONSTRAINT appointments_no_active_overlap
        EXCLUDE USING gist (
            practitioner_id WITH =,
            tstzrange(scheduled_start, scheduled_end, '[)') WITH &&
        ) WHERE (
            is_deleted = false AND status IN
            ('held', 'confirmed', 'checked_in', 'waiting', 'in_progress')
        )
    """)


def downgrade() -> None:
    op.drop_constraint("appointments_no_active_overlap", "appointments")
    op.drop_constraint("appointments_positive_duration", "appointments", type_="check")
    # btree_gist may be shared by other tables and is intentionally retained.
