from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field

from app.schemas import CareConnectBase, TimestampSchema


class LoginRequest(CareConnectBase):
    model_config = ConfigDict(str_strip_whitespace=False, extra="forbid")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, max_length=128, description="User's password")


class RegisterRequest(CareConnectBase):
    model_config = ConfigDict(str_strip_whitespace=False, extra="forbid")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., min_length=12, max_length=128, description="Password (12–128 characters)"
    )


class TokenResponse(CareConnectBase):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class RefreshRequest(CareConnectBase):
    refresh_token: str = Field(..., min_length=1, max_length=4096, description="JWT refresh token")


class PasswordResetRequest(CareConnectBase):
    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirm(CareConnectBase):
    model_config = ConfigDict(str_strip_whitespace=False, extra="forbid")
    token: str = Field(..., min_length=1, max_length=4096, description="Reset token")
    new_password: str = Field(..., min_length=12, max_length=128, description="New password")


class SessionInfo(TimestampSchema):
    id: UUID = Field(..., description="Session ID")
    device: str | None = Field(None, description="Device information")
    ip_address: str | None = Field(None, description="IP address")
    last_active_at: datetime = Field(..., description="Last active timestamp")
    is_current: bool = Field(False, description="Whether this is the current session")
