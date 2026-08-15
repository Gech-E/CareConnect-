from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas import CareConnectBase, TimestampSchema

class UserResponse(TimestampSchema):
    id: UUID = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User's email address")
    phone: str | None = Field(None, description="User's phone number")
    role: Literal["patient", "practitioner", "admin"] = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether user is verified")

class UserUpdate(CareConnectBase):
    phone: str | None = Field(None, description="User's phone number")

class PatientProfileCreate(CareConnectBase):
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    date_of_birth: datetime = Field(..., description="Date of birth")

class PatientProfileUpdate(CareConnectBase):
    first_name: str | None = Field(None, description="First name")
    last_name: str | None = Field(None, description="Last name")
    date_of_birth: datetime | None = Field(None, description="Date of birth")

class PatientProfileResponse(TimestampSchema):
    id: UUID = Field(..., description="Profile ID")
    user_id: UUID = Field(..., description="User ID")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    date_of_birth: datetime = Field(..., description="Date of birth")

class InsurancePolicyCreate(CareConnectBase):
    provider_name: str = Field(..., description="Insurance provider name")
    policy_number: str = Field(..., description="Policy number")
    group_number: str | None = Field(None, description="Group number")

class InsurancePolicyResponse(TimestampSchema):
    id: UUID = Field(..., description="Policy ID")
    patient_id: UUID = Field(..., description="Patient ID")
    provider_name: str = Field(..., description="Insurance provider name")
    policy_number: str = Field(..., description="Policy number")
    group_number: str | None = Field(None, description="Group number")
