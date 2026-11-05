from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import limit_auth_account
from app.core.security import get_current_user
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from app.services import auth_service

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> Any:
    """Register a new user account and return authentication tokens."""
    await limit_auth_account(data.email)
    ip_address = request.client.host if request.client else None
    return await auth_service.register_user(
        db, email=data.email, password=data.password, role="patient", ip_address=ip_address
    )


@router.post("/login")
async def login(
    request: Request,
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> Any:
    """Authenticate a user with email and password."""
    await limit_auth_account(data.email)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "unknown")
    return await auth_service.authenticate_user(
        db, email=data.email, password=data.password, ip_address=ip_address, user_agent=user_agent
    )


@router.post("/refresh")
async def refresh(
    data: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db, scope="function")]
) -> Any:
    """Refresh an access token using a valid refresh token."""
    return await auth_service.refresh_access_token(db, refresh_token=data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    current_user: Annotated[Any, Depends(get_current_user, scope="function")],
) -> None:
    """Invalidate all sessions for the current user."""
    await auth_service.revoke_session(db, current_user.id)
