from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime, timedelta, timezone
import uuid

from app.database import get_db
from app import models, schemas
from app.mock_video import MockVideoAdapter

router = APIRouter(prefix="/api/v1")

# Discovery
@router.get("/practitioners", response_model=List[schemas.PractitionerOut])
async def get_practitioners(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Practitioner).options(selectinload(models.Practitioner.user)))
    practitioners = result.scalars().all()
    return practitioners

@router.get("/practitioners/{id}/availability", response_model=schemas.AvailabilityResponse)
async def get_availability(id: int, date: datetime, db: AsyncSession = Depends(get_db)):
    # Mock availability logic: Return 9 AM to 5 PM slots for the given date
    start_of_day = date.replace(hour=9, minute=0, second=0, microsecond=0)
    slots = []
    for i in range(8):
        slot_start = start_of_day + timedelta(hours=i)
        slot_end = slot_start + timedelta(hours=1)
        slots.append(schemas.TimeSlot(
            start_time=slot_start,
            end_time=slot_end,
            is_available=True
        ))
    
    return schemas.AvailabilityResponse(
        practitioner_id=id,
        date=date,
        slots=slots
    )

# Appointments
mock_holds = {}

@router.post("/appointment-holds", response_model=schemas.AppointmentHoldResponse)
async def create_appointment_hold(request: schemas.AppointmentHoldRequest):
    hold_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Store hold in memory for mock
    mock_holds[hold_id] = {
        "practitioner_id": request.practitioner_id,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "expires_at": expires_at
    }
    
    return schemas.AppointmentHoldResponse(
        hold_id=hold_id,
        expires_at=expires_at,
        practitioner_id=request.practitioner_id,
        start_time=request.start_time,
        end_time=request.end_time
    )

@router.post("/appointments", response_model=schemas.AppointmentResponse)
async def create_appointment(request: schemas.AppointmentCreateRequest, db: AsyncSession = Depends(get_db)):
    if request.hold_id not in mock_holds:
        raise HTTPException(status_code=400, detail="Invalid or expired hold_id")
    
    hold = mock_holds.pop(request.hold_id)
    
    appointment = models.Appointment(
        patient_id=request.patient_id,
        practitioner_id=hold["practitioner_id"],
        start_time=hold["start_time"],
        end_time=hold["end_time"],
        status=models.AppointmentStatus.SCHEDULED
    )
    
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    
    return appointment

@router.post("/appointments/{id}/check-in", response_model=schemas.CheckInResponse)
async def check_in(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Appointment).where(models.Appointment.id == id))
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    appointment.status = models.AppointmentStatus.IN_PROGRESS
    await db.commit()
    
    return schemas.CheckInResponse(status="success", message="Patient checked in successfully")

# Video
@router.post("/appointments/{id}/video-token", response_model=schemas.VideoTokenResponse)
async def get_video_token(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Appointment)
        .options(selectinload(models.Appointment.video_session))
        .where(models.Appointment.id == id)
    )
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if appointment.status != models.AppointmentStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Appointment must be in progress to generate video token")
        
    if not appointment.video_session:
        room_name = f"appointment_{appointment.id}"
        room_sid = MockVideoAdapter.create_room(room_name)
        
        video_session = models.VideoSession(
            appointment_id=appointment.id,
            room_sid=room_sid,
            status="active"
        )
        db.add(video_session)
        await db.commit()
        await db.refresh(video_session)
    else:
        room_sid = appointment.video_session.room_sid
        
    token = MockVideoAdapter.generate_token(identity="user", room_name=room_sid)
    
    return schemas.VideoTokenResponse(
        token=token,
        room_sid=room_sid
    )

# Messaging
@router.get("/message-threads", response_model=List[schemas.MessageThreadOut])
async def get_message_threads(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.MessageThread)
        .options(
            selectinload(models.MessageThread.messages).selectinload(models.Message.attachments)
        )
    )
    return result.scalars().all()

@router.post("/message-threads/{id}/messages", response_model=schemas.MessageOut)
async def create_message(id: int, request: schemas.MessageCreate, db: AsyncSession = Depends(get_db)):
    thread = await db.get(models.MessageThread, id)
    if not thread:
        raise HTTPException(status_code=404, detail="Message thread not found")
        
    message = models.Message(
        thread_id=id,
        sender_id=request.sender_id,
        content=request.content
    )
    db.add(message)
    await db.flush() # to get message.id
    
    # Mock secure upload logic
    for file_name in request.attachment_names:
        short_lived_url = f"https://mock-s3-bucket.s3.amazonaws.com/{uuid.uuid4()}/{file_name}?expires=3600"
        attachment = models.MessageAttachment(
            message_id=message.id,
            file_name=file_name,
            file_url=short_lived_url
        )
        db.add(attachment)
        
    await db.commit()
    await db.refresh(message)
    # Reload with attachments
    result = await db.execute(
        select(models.Message)
        .options(selectinload(models.Message.attachments))
        .where(models.Message.id == message.id)
    )
    return result.scalar_one()

# Records
class MockFHIRAdapter:
    @staticmethod
    def get_patient_records(patient_id: int):
        # Return synthetic records formatted to mimic FHIR extraction
        return [
            models.PatientRecord(
                id=101,
                patient_id=patient_id,
                record_type="clinical_note",
                summary="Patient reported mild fever and cough. Synthetic FHIR data.",
                date_recorded=datetime.now(timezone.utc) - timedelta(days=2)
            ),
            models.PatientRecord(
                id=102,
                patient_id=patient_id,
                record_type="lab_result",
                summary="CBC Panel - Normal. Synthetic FHIR data.",
                date_recorded=datetime.now(timezone.utc) - timedelta(days=1)
            )
        ]

@router.get("/records", response_model=List[schemas.PatientRecordOut])
async def get_records(patient_id: int, db: AsyncSession = Depends(get_db)):
    # Using mock FHIR adapter instead of DB lookup for the sake of the requirement
    records = MockFHIRAdapter.get_patient_records(patient_id)
    return records

@router.get("/records/{id}", response_model=schemas.PatientRecordOut)
async def get_record(id: int, patient_id: int, db: AsyncSession = Depends(get_db)):
    records = MockFHIRAdapter.get_patient_records(patient_id)
    for r in records:
        if r.id == id:
            return r
    raise HTTPException(status_code=404, detail="Record not found")

@router.get("/documents/{id}/download", response_model=schemas.DocumentDownloadResponse)
async def download_document(id: int, db: AsyncSession = Depends(get_db)):
    # Mock short-lived secure URL generation
    mock_url = f"https://mock-secure-storage.careconnect.com/docs/{id}?token={uuid.uuid4().hex}"
    return schemas.DocumentDownloadResponse(url=mock_url)

# Prescriptions
@router.get("/prescriptions", response_model=List[schemas.PrescriptionOut])
async def get_prescriptions(patient_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Prescription).where(models.Prescription.patient_id == patient_id))
    prescriptions = result.scalars().all()
    # Ensure controlled substances are explicitly excluded in mock response
    safe_prescriptions = [p for p in prescriptions if not p.is_controlled_substance]
    
    # If no prescriptions exist in DB, provide some mock data
    if not safe_prescriptions:
        return [
            models.Prescription(
                id=1,
                patient_id=patient_id,
                practitioner_id=1,
                medication_name="Amoxicillin (Synthetic)",
                dosage="500mg",
                instructions="Take 1 tablet twice a day for 7 days",
                is_controlled_substance=False,
                created_at=datetime.now(timezone.utc)
            )
        ]
    return safe_prescriptions

@router.post("/prescriptions/{id}/fulfillment-requests", response_model=schemas.FulfillmentRequestOut)
async def request_fulfillment(id: int, request: schemas.FulfillmentRequestCreate, db: AsyncSession = Depends(get_db)):
    # First ensure the prescription isn't a controlled substance
    result = await db.execute(select(models.Prescription).where(models.Prescription.id == id))
    prescription = result.scalar_one_or_none()
    
    if prescription and prescription.is_controlled_substance:
        raise HTTPException(status_code=400, detail="Cannot fulfill controlled substances online")
        
    fulfillment = models.FulfillmentRequest(
        prescription_id=id,
        pharmacy_id=request.pharmacy_id,
        status="pending"
    )
    db.add(fulfillment)
    await db.commit()
    await db.refresh(fulfillment)
    
    return fulfillment
