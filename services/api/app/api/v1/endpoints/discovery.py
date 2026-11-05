from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any, Optional
from uuid import UUID
from datetime import date
from app.core.database import get_db
from app.services import discovery_service

router = APIRouter()

@router.get("/specialties")
async def get_specialties(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Get list of specialties."""
    return await discovery_service.get_specialties(db)

@router.get("/practitioners")
async def search_practitioners(
    db: Annotated[AsyncSession, Depends(get_db)],
    query: Optional[str] = None,
    specialty: Optional[str] = None
) -> Any:
    """Search for practitioners."""
    return await discovery_service.search_practitioners(db, query=query, specialty=specialty)

@router.get("/practitioners/{id}")
async def get_practitioner(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Get practitioner detail."""
    return await discovery_service.get_practitioner_detail(db, practitioner_id=id)

@router.get("/practitioners/{id}/availability")
async def get_practitioner_availability(
    id: UUID,
    start_date: date,
    end_date: date,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Get practitioner availability."""
    return await discovery_service.get_practitioner_availability(db, practitioner_id=id, start_date=start_date, end_date=end_date)
