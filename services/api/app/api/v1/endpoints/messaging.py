from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any
from uuid import UUID
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services import messaging_service
from app.schemas.messaging import ThreadCreateRequest, MessageCreateRequest

router = APIRouter()

@router.get("/message-threads")
async def get_message_threads(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get user message threads."""
    return await messaging_service.get_user_threads(db, user_id=current_user.id)

@router.post("/message-threads")
async def create_message_thread(
    data: ThreadCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Create a new message thread."""
    return await messaging_service.create_thread(db, creator_id=current_user.id, creator_role=current_user.role, **data.model_dump())

@router.get("/message-threads/{id}/messages")
async def get_thread_messages(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Get messages for a thread."""
    return await messaging_service.get_thread_messages(db, thread_id=id, user_id=current_user.id)

@router.post("/message-threads/{id}/messages")
async def send_message(
    id: UUID,
    data: MessageCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Send a message to a thread."""
    return await messaging_service.send_message(
        db,
        thread_id=id,
        sender_id=current_user.id,
        sender_role=current_user.role,
        body=data.body
    )

@router.post("/message-threads/{id}/read")
async def mark_messages_read(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> Any:
    """Mark thread messages as read."""
    return await messaging_service.mark_messages_read(db, thread_id=id, user_id=current_user.id)
