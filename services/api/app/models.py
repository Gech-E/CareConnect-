from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
from app.database import Base

class UserRole(str, enum.Enum):
    PATIENT = "patient"
    PRACTITIONER = "practitioner"
    ADMIN = "admin"

class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"
    NO_SHOW = "no_show"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.PATIENT)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Practitioner(Base):
    __tablename__ = "practitioners"

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    specialty = Column(String, nullable=False)
    bio = Column(Text, nullable=True)
    is_available = Column(Boolean, default=True)
    
    user = relationship("User")
    appointments = relationship("Appointment", back_populates="practitioner")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    practitioner_id = Column(Integer, ForeignKey("practitioners.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("User")
    practitioner = relationship("Practitioner", back_populates="appointments")
    video_session = relationship("VideoSession", back_populates="appointment", uselist=False)

class VideoSession(Base):
    __tablename__ = "video_sessions"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True, nullable=False)
    room_sid = Column(String, unique=True, nullable=True)
    status = Column(String, default="created") # created, active, ended
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    appointment = relationship("Appointment", back_populates="video_session")

# Messaging Models
class MessageThread(Base):
    __tablename__ = "message_threads"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    practitioner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("User", foreign_keys=[patient_id])
    practitioner = relationship("User", foreign_keys=[practitioner_id])
    messages = relationship("Message", back_populates="thread")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("message_threads.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    thread = relationship("MessageThread", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    attachments = relationship("MessageAttachment", back_populates="message")

class MessageAttachment(Base):
    __tablename__ = "message_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=False) # e.g., short-lived S3 pre-signed URL
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    message = relationship("Message", back_populates="attachments")

# Records Models
class PatientRecord(Base):
    __tablename__ = "patient_records"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    record_type = Column(String, nullable=False) # e.g., lab_result, clinical_note
    summary = Column(Text, nullable=True)
    date_recorded = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    patient = relationship("User", foreign_keys=[patient_id])
    documents = relationship("Document", back_populates="record")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("patient_records.id"), nullable=True)
    title = Column(String, nullable=False)
    document_url = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    record = relationship("PatientRecord", back_populates="documents")

# Prescriptions Models
class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    practitioner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medication_name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    instructions = Column(Text, nullable=True)
    is_controlled_substance = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class FulfillmentRequest(Base):
    __tablename__ = "fulfillment_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False)
    pharmacy_id = Column(String, nullable=False)
    status = Column(String, default="pending") # pending, accepted, rejected, fulfilled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
