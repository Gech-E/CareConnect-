from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas import CareConnectBase, TimestampSchema

class UserSearchParams(CareConnectBase):
    email: str | None = Field(None, description="Search by email")
    role: str | None = Field(None, description="Filter by role")
    status: str | None = Field(None, description="Filter by status")

class AppointmentSearchParams(CareConnectBase):
    date_from: datetime | None = Field(None, description="Start date")
    date_to: datetime | None = Field(None, description="End date")
    status: str | None = Field(None, description="Filter by status")
    practitioner_id: UUID | None = Field(None, description="Filter by practitioner")

class AuditEventResponse(TimestampSchema):
    id: UUID = Field(..., description="Event ID")
    actor_id: UUID | None = Field(None, description="ID of the user who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: UUID | None = Field(None, description="ID of resource affected")
    ip_address: str | None = Field(None, description="IP address")
    details: dict[str, Any] = Field(default_factory=dict, description="Event details")

class AuditSearchParams(CareConnectBase):
    actor_id: UUID | None = Field(None, description="Filter by actor")
    action: str | None = Field(None, description="Filter by action")
    resource_type: str | None = Field(None, description="Filter by resource type")
    date_from: datetime | None = Field(None, description="Start date")
    date_to: datetime | None = Field(None, description="End date")

class IntegrationHealthResponse(CareConnectBase):
    service_name: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    last_check: datetime = Field(..., description="Last check timestamp")
    details: dict[str, Any] = Field(default_factory=dict, description="Health details")

class SuspendRequest(CareConnectBase):
    reason: str = Field(..., description="Reason for suspension")
