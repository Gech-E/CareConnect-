from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas import CareConnectBase, TimestampSchema

class EncounterResponse(TimestampSchema):
    id: UUID = Field(..., description="Encounter ID")
    appointment_id: UUID = Field(..., description="Appointment ID")
    patient_id: UUID = Field(..., description="Patient ID")
    practitioner_id: UUID = Field(..., description="Practitioner ID")
    status: str = Field(..., description="Encounter status")
    notes: str | None = Field(None, description="Clinical notes")

class VideoTokenResponse(CareConnectBase):
    token: str = Field(..., description="Video room token")
    session_id: str = Field(..., description="Video session ID")
    expires_at: datetime = Field(..., description="Token expiration")

class DeviceCheckRequest(CareConnectBase):
    has_camera: bool = Field(..., description="Camera detected")
    has_microphone: bool = Field(..., description="Microphone detected")
    has_speaker: bool = Field(..., description="Speaker detected")
    network_quality: str = Field(..., description="Network quality assessment")

class DeviceCheckResponse(CareConnectBase):
    ready: bool = Field(..., description="Whether devices are ready")
    issues: list[str] = Field(default_factory=list, description="List of issues")

class VideoEventRequest(CareConnectBase):
    event_type: str = Field(..., description="Event type")
    timestamp: datetime = Field(..., description="Event timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Event metadata")
