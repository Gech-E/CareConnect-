from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas import CareConnectBase, TimestampSchema

class NotificationResponse(TimestampSchema):
    id: UUID = Field(..., description="Notification ID")
    user_id: UUID = Field(..., description="User ID")
    type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body (PHI-safe)")
    is_read: bool = Field(False, description="Whether the notification has been read")
    action_url: str | None = Field(None, description="URL for action")

class NotificationPreferences(CareConnectBase):
    email_appointments: bool = Field(True, description="Email notifications for appointments")
    sms_appointments: bool = Field(True, description="SMS notifications for appointments")
    push_appointments: bool = Field(True, description="Push notifications for appointments")
    email_messages: bool = Field(True, description="Email notifications for messages")
    push_messages: bool = Field(True, description="Push notifications for messages")
    email_marketing: bool = Field(False, description="Email notifications for marketing")
