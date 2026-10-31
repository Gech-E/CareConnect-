from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas import CareConnectBase, TimestampSchema

class AvailabilityRuleCreate(CareConnectBase):
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday)")
    start_time: str = Field(..., description="Start time (HH:MM)")
    end_time: str = Field(..., description="End time (HH:MM)")
    visit_duration_minutes: int = Field(..., description="Visit duration in minutes")
    buffer_minutes: int = Field(..., description="Buffer time between visits in minutes")
    timezone: str = Field(..., description="Timezone string")

class AvailabilityRuleResponse(TimestampSchema):
    id: UUID = Field(..., description="Rule ID")
    practitioner_id: UUID = Field(..., description="Practitioner ID")
    day_of_week: int = Field(..., description="Day of week")
    start_time: str = Field(..., description="Start time")
    end_time: str = Field(..., description="End time")
    visit_duration_minutes: int = Field(..., description="Visit duration")
    buffer_minutes: int = Field(..., description="Buffer time")
    timezone: str = Field(..., description="Timezone string")

class AvailabilitySlot(CareConnectBase):
    start: datetime = Field(..., description="Slot start time")
    end: datetime = Field(..., description="Slot end time")
    is_available: bool = Field(..., description="Whether the slot is available")

class AvailabilityExceptionCreate(CareConnectBase):
    start_time: datetime = Field(..., description="Exception start time")
    end_time: datetime = Field(..., description="Exception end time")
    is_available: bool = Field(False, description="Whether this exception makes the time available or unavailable")

class AvailabilityResponse(CareConnectBase):
    date: datetime = Field(..., description="Date of availability")
    slots: list[AvailabilitySlot] = Field(..., description="Available slots for the date")
