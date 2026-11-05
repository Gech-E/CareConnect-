from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, EmailStr, Field, field_validator

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
    legal_first_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("legal_first_name", "first_name"),
    )
    legal_last_name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("legal_last_name", "last_name"),
    )
    date_of_birth: date | None = None

    @field_validator("date_of_birth")
    @classmethod
    def valid_birth_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value


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
