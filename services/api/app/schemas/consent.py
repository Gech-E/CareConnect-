from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas import CareConnectBase, TimestampSchema

class ConsentCreateRequest(CareConnectBase):
    consent_type: str = Field(..., description="Type of consent")
    version: str = Field(..., description="Consent document version")

class ConsentResponse(TimestampSchema):
    id: UUID = Field(..., description="Consent ID")
    patient_id: UUID = Field(..., description="Patient ID")
    consent_type: str = Field(..., description="Type of consent")
    version: str = Field(..., description="Version")
    agreed_at: datetime = Field(..., description="Time agreed")
    ip_address: str | None = Field(None, description="IP address")

class ConsentHistoryResponse(CareConnectBase):
    consents: list[ConsentResponse] = Field(..., description="List of consents")
