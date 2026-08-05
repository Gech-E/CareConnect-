from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from app.models import UserRole, AppointmentStatus

# Practitioner Schemas
class PractitionerBase(BaseModel):
    specialty: str
    bio: Optional[str] = None
    is_available: bool = True

class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True

class PractitionerOut(PractitionerBase):
    id: int
    user: UserOut

    class Config:
        from_attributes = True

# Availability Schema
class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    is_available: bool

class AvailabilityResponse(BaseModel):
    practitioner_id: int
    date: datetime
    slots: List[TimeSlot]

# Appointment Schemas
class AppointmentHoldRequest(BaseModel):
    practitioner_id: int
    start_time: datetime
    end_time: datetime

class AppointmentHoldResponse(BaseModel):
    hold_id: str
    expires_at: datetime
    practitioner_id: int
    start_time: datetime
    end_time: datetime

class AppointmentCreateRequest(BaseModel):
    hold_id: str
    patient_id: int

class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    practitioner_id: int
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus

    class Config:
        from_attributes = True

class CheckInResponse(BaseModel):
    status: str
    message: str

class VideoTokenResponse(BaseModel):
    token: str
    room_sid: str

# Messaging Schemas
class MessageAttachmentOut(BaseModel):
    id: int
    file_name: str
    file_url: str

    class Config:
        from_attributes = True

class MessageOut(BaseModel):
    id: int
    thread_id: int
    sender_id: int
    content: str
    created_at: datetime
    attachments: List[MessageAttachmentOut] = []

    class Config:
        from_attributes = True

class MessageThreadOut(BaseModel):
    id: int
    patient_id: int
    practitioner_id: int
    created_at: datetime
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    sender_id: int
    content: str
    attachment_names: List[str] = [] # Optional filenames if uploading attachments

# Records Schemas
class DocumentOut(BaseModel):
    id: int
    title: str
    document_url: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class PatientRecordOut(BaseModel):
    id: int
    patient_id: int
    record_type: str
    summary: Optional[str] = None
    date_recorded: datetime
    documents: List[DocumentOut] = [] # Assuming we attach documents to records for now, or fetch separately

    class Config:
        from_attributes = True

class DocumentDownloadResponse(BaseModel):
    url: str # Short-lived secure URL

# Prescriptions Schemas
class PrescriptionOut(BaseModel):
    id: int
    patient_id: int
    practitioner_id: int
    medication_name: str
    dosage: str
    instructions: Optional[str]
    is_controlled_substance: bool
    created_at: datetime

    class Config:
        from_attributes = True

class FulfillmentRequestCreate(BaseModel):
    pharmacy_id: str

class FulfillmentRequestOut(BaseModel):
    id: int
    prescription_id: int
    pharmacy_id: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
