from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services import video_service
from app.schemas.encounter import DeviceCheckRequest, VideoEventRequest

router = APIRouter(prefix="/appointments")

@router.post("/{appointment_id}/device-check")
async def device_check(
    appointment_id: UUID,
    data: DeviceCheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Run device check."""
    return await video_service.run_device_check(data)

@router.post("/{appointment_id}/video-token")
async def get_video_token(
    appointment_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get video token."""
    ip_address = request.client.host if request.client else None
    return await video_service.create_video_token(
        db,
        appointment_id=appointment_id,
        user_id=current_user.id,
        user_role=current_user.role,
        ip_address=ip_address
    )

@router.post("/{appointment_id}/video-events")
async def record_video_event(
    appointment_id: UUID,
    data: VideoEventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Record video event."""
    return await video_service.record_video_event(db, appointment_id=appointment_id, event_data=data)

@router.post("/{appointment_id}/end-visit")
async def end_visit(
    appointment_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """End the video visit."""
    ip_address = request.client.host if request.client else None
    return await video_service.end_visit(
        db,
        appointment_id=appointment_id,
        user_id=current_user.id,
        user_role=current_user.role,
        ip_address=ip_address
    )
