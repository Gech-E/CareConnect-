from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas import CareConnectBase, TimestampSchema

class LoginRequest(CareConnectBase):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

class RegisterRequest(CareConnectBase):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    role: Literal["patient", "practitioner", "admin"] = Field("patient", description="User role")

class TokenResponse(CareConnectBase):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")

class RefreshRequest(CareConnectBase):
    refresh_token: str = Field(..., description="JWT refresh token")

class PasswordResetRequest(CareConnectBase):
    email: EmailStr = Field(..., description="User's email address")

class PasswordResetConfirm(CareConnectBase):
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., description="New password")

class SessionInfo(TimestampSchema):
    id: UUID = Field(..., description="Session ID")
    device: str | None = Field(None, description="Device information")
    ip_address: str | None = Field(None, description="IP address")
    last_active_at: datetime = Field(..., description="Last active timestamp")
    is_current: bool = Field(False, description="Whether this is the current session")
