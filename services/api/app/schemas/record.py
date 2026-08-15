from datetime import datetime
from uuid import UUID

from pydantic import Field

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
    filename: str = Field(..., description="Name of the file")
    content_type: str = Field(..., description="MIME type")
    context_type: str = Field(..., description="Context type (e.g. appointment, record)")
    context_id: UUID = Field(..., description="Context ID")

class DocumentUploadIntentResponse(CareConnectBase):
    document_id: UUID = Field(..., description="Document ID")
    upload_url: str = Field(..., description="Presigned upload URL")
    expires_at: datetime = Field(..., description="URL expiration time")

class DocumentCompleteRequest(CareConnectBase):
    content_hash: str = Field(..., description="File content hash for verification")

class DocumentDownloadResponse(CareConnectBase):
    download_url: str = Field(..., description="Presigned download URL")
    expires_at: datetime = Field(..., description="URL expiration time")
