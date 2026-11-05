from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.record import DocumentContextType
from app.schemas import CareConnectBase, TimestampSchema


class RecordResponse(TimestampSchema):
    id: UUID = Field(..., description="Record ID")
    patient_id: UUID = Field(..., description="Patient ID")
    record_type: str = Field(..., description="Type of record")
    title: str = Field(..., description="Title of the record")
    date: datetime = Field(..., description="Date of the record")
    practitioner_id: UUID | None = Field(None, description="Practitioner who created the record")
    notes: str | None = Field(None, description="Clinical notes or description")
    document_ids: list[UUID] = Field(default_factory=list, description="Associated document IDs")


class RecordListParams(CareConnectBase):
    type_filter: str | None = Field(None, description="Filter by record type")
    date_from: datetime | None = Field(None, description="Start date")
    date_to: datetime | None = Field(None, description="End date")
    search: str | None = Field(None, description="Search query")


class DocumentUploadIntentRequest(CareConnectBase):
    filename: str = Field(..., min_length=1, max_length=255, description="Name of the file")
    content_type: str = Field(..., min_length=1, max_length=100, description="MIME type")
    context_type: DocumentContextType = Field(..., description="Context type")
    context_id: UUID = Field(..., description="Context ID")


class DocumentUploadIntentResponse(CareConnectBase):
    document_id: UUID = Field(..., description="Document ID")
    upload_url: str = Field(..., description="Presigned upload URL")
    expires_at: datetime = Field(..., description="URL expiration time")


class DocumentCompleteRequest(CareConnectBase):
    content_hash: str = Field(
        ...,
        pattern=r"^[0-9a-fA-F]{64}$",
        description="SHA-256 hash claimed by the client; verified by the scanner",
    )


class DocumentDownloadResponse(CareConnectBase):
    download_url: str = Field(..., description="Presigned download URL")
    expires_at: datetime = Field(..., description="URL expiration time")
