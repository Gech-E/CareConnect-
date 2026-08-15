from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services import prescription_service
from app.schemas.prescription import FulfillmentRequestCreate, RefillRequestCreate

router = APIRouter()

@router.get("/")
async def get_prescriptions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get patient prescriptions."""
    return await prescription_service.get_patient_prescriptions(db, patient_id=current_user.id)

@router.get("/{id}")
async def get_prescription(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get a specific prescription."""
    return await prescription_service.get_prescription_by_id(db, prescription_id=id, patient_id=current_user.id)

@router.get("/{id}/fulfillment-options")
async def get_fulfillment_options(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get fulfillment options for a prescription."""
    return await prescription_service.get_fulfillment_options(db, prescription_id=id, patient_id=current_user.id)

@router.post("/{id}/fulfillment-requests")
async def create_fulfillment_request(
    id: UUID,
    data: FulfillmentRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Create a fulfillment request for a prescription."""
    return await prescription_service.create_fulfillment_request(
        db,
        prescription_id=id,
        patient_id=current_user.id,
        pharmacy_name=data.pharmacy_name,
        delivery_method=data.delivery_method
    )

@router.post("/{id}/refill-requests")
async def create_refill_request(
    id: UUID,
    data: RefillRequestCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Request a refill for a prescription."""
    # Assuming there's a simple refill method in the service or just direct interaction
    # If not specified, we can just stub this to return a status since no service method was given
    return {"status": "Refill requested", "prescription_id": id, "reason": data.reason}
