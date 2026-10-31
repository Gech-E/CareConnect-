from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services import record_service
from app.schemas.record import DocumentUploadIntentRequest, DocumentCompleteRequest

router = APIRouter()

@router.get("/records")
async def get_records(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get patient records."""
    return await record_service.get_patient_records(db, patient_id=current_user.id)

@router.get("/records/{id}")
async def get_record(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get a specific record."""
    return await record_service.get_record_by_id(db, record_id=id, patient_id=current_user.id)

@router.post("/documents/upload-intents")
async def create_upload_intent(
    data: DocumentUploadIntentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Create an upload intent for a document."""
    return await record_service.create_upload_intent(
        db,
        owner_id=current_user.id,
        filename=data.filename,
        content_type=data.content_type,
        context_type=data.context_type,
        context_id=data.context_id
    )

@router.post("/documents/{id}/complete")
async def complete_document_upload(
    id: UUID,
    data: DocumentCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Complete a document upload."""
    return await record_service.complete_upload(
        db,
        document_id=id,
        owner_id=current_user.id,
        content_hash=data.content_hash
    )

@router.get("/documents/{id}/download")
async def get_document_download_url(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get download URL for a document."""
    return await record_service.get_download_url(
        db,
        document_id=id,
        user_id=current_user.id,
        user_role=current_user.role
    )
