from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas import CareConnectBase, TimestampSchema

class OrganizationResponse(TimestampSchema):
    id: UUID = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")

class PractitionerRoleResponse(TimestampSchema):
    id: UUID = Field(..., description="Role ID")
    organization_id: UUID = Field(..., description="Organization ID")
    role_name: str = Field(..., description="Role name")

class PractitionerResponse(TimestampSchema):
    id: UUID = Field(..., description="Practitioner ID")
    user_id: UUID = Field(..., description="User ID")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    credentials: list[str] = Field(..., description="Credentials (e.g. MD, DO)")
    specialty: str = Field(..., description="Medical specialty")
    rating: float = Field(..., description="Average rating")
    price: float = Field(..., description="Consultation price")
    roles: list[PractitionerRoleResponse] = Field(..., description="Practitioner roles")
    organization: OrganizationResponse | None = Field(None, description="Primary organization")

class PractitionerSummary(CareConnectBase):
    id: UUID = Field(..., description="Practitioner ID")
    name: str = Field(..., description="Full name")
    credentials: list[str] = Field(..., description="Credentials")
    specialty: str = Field(..., description="Specialty")
    rating: float = Field(..., description="Average rating")
    price: float = Field(..., description="Consultation price")
    next_available_slot: datetime | None = Field(None, description="Next available appointment slot")

class PractitionerSearch(CareConnectBase):
    name: str | None = Field(None, description="Search by name")
    specialty: str | None = Field(None, description="Search by specialty")
    language: str | None = Field(None, description="Search by language")
    visit_type: str | None = Field(None, description="Visit type")
    min_rating: float | None = Field(None, description="Minimum rating")
    max_price: float | None = Field(None, description="Maximum price")
    available_date: datetime | None = Field(None, description="Available date")
    sort_by: Literal["rating", "price", "availability"] | None = Field(None, description="Sort order")
