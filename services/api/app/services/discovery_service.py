"""Practitioner discovery and availability service.

Implements SRS §4.3-4.5: search, filters, availability generation,
and slot calculation with timezone awareness.
"""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError

logger = structlog.get_logger(__name__)


async def search_practitioners(
    db: AsyncSession,
    *,
    query: str | None = None,
    specialty: str | None = None,
    language: str | None = None,
    visit_type: str | None = None,
    min_rating: float | None = None,
    max_price: float | None = None,
    available_date: date | None = None,
    sort_by: str = "recommended",
    limit: int = 20,
    cursor: str | None = None,
) -> dict:
    """Search and filter practitioners (DISC-001 through DISC-007)."""
    from app.models.practitioner import Practitioner, PractitionerRole

    stmt = (
        select(Practitioner)
        .join(PractitionerRole, Practitioner.id == PractitionerRole.practitioner_id)
        .where(Practitioner.status == "active")
    )

    # Name search
    if query:
        search_term = f"%{query.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Practitioner.first_name).like(search_term),
                func.lower(Practitioner.last_name).like(search_term),
                func.lower(Practitioner.credentials).like(search_term),
            )
        )

    # Specialty filter
    if specialty:
        stmt = stmt.where(func.lower(PractitionerRole.specialty) == specialty.lower())

    # Rating filter
    if min_rating is not None:
        stmt = stmt.where(Practitioner.average_rating >= min_rating)

    # Price filter
    if max_price is not None:
        stmt = stmt.where(PractitionerRole.price_range_min <= max_price)

    # Language filter (JSONB contains)
    if language:
        stmt = stmt.where(PractitionerRole.languages.contains([language]))

    # Visit type filter
    if visit_type:
        stmt = stmt.where(PractitionerRole.visit_types.contains([visit_type]))

    # Sorting
    if sort_by == "rating":
        stmt = stmt.order_by(Practitioner.average_rating.desc().nullslast())
    elif sort_by == "price":
        stmt = stmt.order_by(PractitionerRole.price_range_min.asc().nullslast())
    elif sort_by == "soonest":
        stmt = stmt.order_by(Practitioner.created_at.asc())  # Simplified; real would use availability
    else:  # recommended
        stmt = stmt.order_by(
            Practitioner.average_rating.desc().nullslast(),
            Practitioner.review_count.desc(),
        )

    stmt = stmt.distinct().limit(limit + 1)

    result = await db.execute(stmt)
    practitioners = result.scalars().all()

    has_more = len(practitioners) > limit
    if has_more:
        practitioners = practitioners[:limit]

    return {
        "items": [_practitioner_summary(p) for p in practitioners],
        "next_cursor": str(practitioners[-1].id) if has_more else None,
        "has_more": has_more,
    }


async def get_practitioner_detail(
    db: AsyncSession,
    practitioner_id: UUID,
) -> dict:
    """Get full practitioner profile (PROF-001 through PROF-005)."""
    from app.models.practitioner import Practitioner, PractitionerRole

    result = await db.execute(
        select(Practitioner).where(Practitioner.id == practitioner_id)
    )
    practitioner = result.scalar_one_or_none()
    if not practitioner:
        raise NotFoundError("practitioner")

    roles_result = await db.execute(
        select(PractitionerRole).where(PractitionerRole.practitioner_id == practitioner_id)
    )
    roles = roles_result.scalars().all()

    return {
        "id": str(practitioner.id),
        "first_name": practitioner.first_name,
        "last_name": practitioner.last_name,
        "credentials": practitioner.credentials,
        "bio": practitioner.bio,
        "years_of_experience": practitioner.years_of_experience,
        "profile_image_url": practitioner.profile_image_url,
        "status": practitioner.status,
        "average_rating": float(practitioner.average_rating) if practitioner.average_rating else None,
        "review_count": practitioner.review_count or 0,
        "roles": [
            {
                "id": str(r.id),
                "specialty": r.specialty,
                "languages": r.languages or [],
                "service_areas": r.service_areas or [],
                "visit_types": r.visit_types or [],
                "price_range_min": float(r.price_range_min) if r.price_range_min else None,
                "price_range_max": float(r.price_range_max) if r.price_range_max else None,
            }
            for r in roles
        ],
    }


async def get_practitioner_availability(
    db: AsyncSession,
    practitioner_id: UUID,
    start_date: date,
    end_date: date | None = None,
) -> dict:
    """Generate available slots from availability rules (APT-002)."""
    from app.models.availability import AvailabilityException, AvailabilityRule

    if not end_date:
        end_date = start_date + timedelta(days=7)

    # Fetch rules
    rules_result = await db.execute(
        select(AvailabilityRule).where(
            AvailabilityRule.practitioner_id == practitioner_id,
            AvailabilityRule.is_active == True,  # noqa: E712
        )
    )
    rules = rules_result.scalars().all()

    # Fetch exceptions
    exceptions_result = await db.execute(
        select(AvailabilityException).where(
            AvailabilityException.practitioner_id == practitioner_id,
            AvailabilityException.date >= start_date,
            AvailabilityException.date <= end_date,
        )
    )
    exceptions = {e.date: e for e in exceptions_result.scalars().all()}

    # Fetch existing appointments to exclude booked slots
    from app.models.appointment import Appointment

    appt_result = await db.execute(
        select(Appointment).where(
            Appointment.practitioner_id == practitioner_id,
            Appointment.status.in_(["held", "confirmed", "checked_in", "waiting", "in_progress"]),
            Appointment.scheduled_start >= datetime.combine(start_date, time.min).replace(tzinfo=UTC),
            Appointment.scheduled_start <= datetime.combine(end_date, time.max).replace(tzinfo=UTC),
        )
    )
    booked_slots = [
        (a.scheduled_start, a.scheduled_end)
        for a in appt_result.scalars().all()
    ]

    # Generate slots
    availability_by_date = {}
    current_date = start_date
    while current_date <= end_date:
        day_of_week = current_date.weekday()
        day_slots = []

        # Check exceptions
        if current_date in exceptions:
            exc = exceptions[current_date]
            if not exc.is_available:
                availability_by_date[current_date.isoformat()] = []
                current_date += timedelta(days=1)
                continue

        # Apply rules for this day
        for rule in rules:
            if rule.day_of_week != day_of_week:
                continue

            slot_start = datetime.combine(current_date, rule.start_time).replace(tzinfo=UTC)
            slot_end_limit = datetime.combine(current_date, rule.end_time).replace(tzinfo=UTC)
            duration = timedelta(minutes=rule.visit_duration_minutes)
            buffer = timedelta(minutes=rule.buffer_minutes or 0)

            while slot_start + duration <= slot_end_limit:
                slot_end = slot_start + duration
                is_booked = any(
                    bs < slot_end and be > slot_start
                    for bs, be in booked_slots
                )
                day_slots.append({
                    "start": slot_start.isoformat(),
                    "end": slot_end.isoformat(),
                    "is_available": not is_booked,
                })
                slot_start = slot_end + buffer

        availability_by_date[current_date.isoformat()] = day_slots
        current_date += timedelta(days=1)

    return {
        "practitioner_id": str(practitioner_id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "availability": availability_by_date,
    }


async def get_specialties(db: AsyncSession) -> list[dict]:
    """List all available specialties."""
    from app.models.practitioner import PractitionerRole

    result = await db.execute(
        select(PractitionerRole.specialty)
        .distinct()
        .where(PractitionerRole.specialty.isnot(None))
        .order_by(PractitionerRole.specialty)
    )
    specialties = result.scalars().all()
    return [{"name": s, "slug": s.lower().replace(" ", "-")} for s in specialties]


def _practitioner_summary(p) -> dict:
    """Convert practitioner to summary dict for list views."""
    return {
        "id": str(p.id),
        "first_name": p.first_name,
        "last_name": p.last_name,
        "credentials": p.credentials,
        "profile_image_url": p.profile_image_url,
        "average_rating": float(p.average_rating) if p.average_rating else None,
        "review_count": p.review_count or 0,
        "status": p.status,
    }
