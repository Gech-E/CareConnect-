from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any
from app.core.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest
from app.services import auth_service
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Register a new user account and return authentication tokens."""
    ip_address = request.client.host if request.client else None
    return await auth_service.register_user(
        db,
        email=data.email,
        password=data.password,
        role=data.role,
        ip_address=ip_address
    )

@router.post("/login")
async def login(
    request: Request,
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Authenticate a user with email and password."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "unknown")
    return await auth_service.authenticate_user(
        db,
        email=data.email,
        password=data.password,
        ip_address=ip_address,
        user_agent=user_agent
    )

@router.post("/refresh")
async def refresh(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Refresh an access token using a valid refresh token."""
    return await auth_service.refresh_access_token(
        db,
        refresh_token=data.refresh_token
    )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Any, Depends(get_current_active_user)]
) -> None:
    """Invalidate all sessions for the current user."""
    from sqlalchemy import delete
    from app.models.user import UserSession
    await db.execute(
        delete(UserSession).where(UserSession.user_id == current_user.id)
    )

