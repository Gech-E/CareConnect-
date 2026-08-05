from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

class AuditEvent(BaseModel):
    id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    timestamp: datetime
    outcome: str

class MockUser(BaseModel):
    id: str
    name: str
    role: str

@router.get("/users", response_model=List[MockUser])
async def get_users():
    return [
        {"id": "usr-1", "name": "Getachew Ekubay", "role": "admin"},
        {"id": "usr-2", "name": "Dr. Sarah Jenkins", "role": "clinician"}
    ]

@router.get("/appointments")
async def get_appointments():
    return [
        {"id": "apt-1", "patient_id": "usr-3", "clinician_id": "usr-2", "status": "completed"}
    ]

@router.get("/audit-events", response_model=List[AuditEvent])
async def get_audit_events():
    return [
        {
            "id": "evt-1",
            "actor": "usr-1",
            "action": "view_records",
            "resource_type": "MedicalRecord",
            "resource_id": "rec-1",
            "timestamp": datetime.utcnow(),
            "outcome": "success"
        }
    ]
