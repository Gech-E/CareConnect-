from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.schemas import CareConnectBase, TimestampSchema
from app.schemas.practitioner import PractitionerSummary


class AppointmentHoldRequest(CareConnectBase):
    practitioner_id: UUID = Field(..., description="Practitioner ID")
    slot_start: AwareDatetime = Field(..., description="Slot start time with UTC offset")
    visit_type: str = Field(..., min_length=1, max_length=100, description="Type of visit")
    idempotency_key: str = Field(
        ..., min_length=16, max_length=255, description="Idempotency key for hold"
    )


class AppointmentHoldResponse(CareConnectBase):
    hold_id: UUID = Field(..., description="Hold ID")
    expires_at: datetime = Field(..., description="Expiration time")


class AppointmentCreateRequest(CareConnectBase):
    hold_id: UUID = Field(..., description="Hold ID")
    preparation_notes: str | None = Field(None, max_length=5000, description="Patient notes")
    idempotency_key: str = Field(
        ..., min_length=16, max_length=255, description="Idempotency key for creation"
    )


class AppointmentResponse(TimestampSchema):
    id: UUID = Field(..., description="Appointment ID")
    patient_id: UUID = Field(..., description="Patient ID")
    practitioner: PractitionerSummary = Field(..., description="Practitioner info")
    slot_start: datetime = Field(..., description="Start time")
    slot_end: datetime = Field(..., description="End time")
    visit_type: str = Field(..., description="Visit type")
    status: Literal["scheduled", "in_progress", "completed", "cancelled", "no_show"] = Field(
        ..., description="Appointment status"
    )
    preparation_notes: str | None = Field(None, description="Preparation notes")
    status_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Status change history"
    )


class AppointmentListResponse(CareConnectBase):
    id: UUID = Field(..., description="Appointment ID")
    practitioner: PractitionerSummary = Field(..., description="Practitioner info")
    slot_start: datetime = Field(..., description="Start time")
    visit_type: str = Field(..., description="Visit type")
    status: Literal["scheduled", "in_progress", "completed", "cancelled", "no_show"] = Field(
        ..., description="Status"
    )


class RescheduleRequest(CareConnectBase):
    new_slot_start: AwareDatetime = Field(..., description="New slot start time with UTC offset")
    reason: str | None = Field(None, max_length=255, description="Reason for reschedule")


class CancelRequest(CareConnectBase):
    reason: str | None = Field(None, max_length=255, description="Reason for cancellation")


class CheckInRequest(CareConnectBase):
    location_confirmed: bool = Field(..., description="Location confirmed")
    emergency_contact_confirmed: bool = Field(..., description="Emergency contact confirmed")


class CalendarExportResponse(CareConnectBase):
    ical_data: str = Field(..., description="iCal format data")


# Aliases for endpoint compatibility
AppointmentConfirmRequest = AppointmentCreateRequest
AppointmentRescheduleRequest = RescheduleRequest
AppointmentCancelRequest = CancelRequest
AppointmentCheckInRequest = CheckInRequest
