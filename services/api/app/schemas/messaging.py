from uuid import UUID

from pydantic import Field

from app.schemas import CareConnectBase, TimestampSchema

class ThreadCreateRequest(CareConnectBase):
    participant_ids: list[UUID] = Field(..., description="Participant user IDs")
    appointment_id: UUID | None = Field(None, description="Related appointment ID")
    subject: str = Field(..., description="Thread subject")

class MessageResponse(TimestampSchema):
    id: UUID = Field(..., description="Message ID")
    thread_id: UUID = Field(..., description="Thread ID")
    sender_id: UUID = Field(..., description="Sender ID")
    body: str = Field(..., description="Message body")
    attachment_document_id: UUID | None = Field(None, description="Attachment document ID")

class ThreadResponse(TimestampSchema):
    id: UUID = Field(..., description="Thread ID")
    subject: str = Field(..., description="Subject")
    participants: list[UUID] = Field(..., description="Participants")
    appointment_id: UUID | None = Field(None, description="Appointment ID")
    last_message_preview: str | None = Field(None, description="Last message snippet")

class MessageCreateRequest(CareConnectBase):
    body: str = Field(..., description="Message text")
    attachment_document_id: UUID | None = Field(None, description="Attachment document ID")

class MarkReadRequest(CareConnectBase):
    message_ids: list[UUID] = Field(..., description="Messages to mark as read")
