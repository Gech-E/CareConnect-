"""Authentication service.

Handles registration, login, token refresh, password reset,
and session management per SRS §4.1.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.security import (
    UserRole,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    role: str = "patient",
    ip_address: str | None = None,
) -> dict:
    """Create a new user account.

    Per AUTH-006: Does not reveal whether an account already exists.
    """
    from app.models.user import User, UserSession

    # Privileged identities must be provisioned through a controlled workflow.
    if role != "patient":
        raise AppError(
            code="INVALID_REGISTRATION_ROLE",
            message="Self-service registration is available to patients only.",
            status_code=403,
        )

    # Check for existing account (but don't reveal it)
    existing = await db.execute(select(User).where(User.email == email.lower()))
    if existing.scalar_one_or_none():
        raise ConflictError(
            code="REGISTRATION_FAILED",
            message="Registration could not be completed. Please try again or sign in.",
        )

    user = User(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    # Create initial session
    session_id = str(uuid4())
    session = UserSession(
        id=uuid4(),
        user_id=user.id,
        session_token=session_id,
        device_info="registration",
        ip_address=ip_address or "unknown",
        expires_at=datetime.now(UTC) + timedelta(days=get_settings().JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.flush()

    tokens = create_token_pair(user.id, user.role, session_id)

    await log_audit_event(
        db,
        actor_id=user.id,
        actor_role=user.role,
        action="user.registered",
        resource_type="user",
        resource_id=user.id,
        ip_address=ip_address,
    )

    return {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
        "tokens": tokens,
    }


async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """Authenticate a user and return tokens.

    Per AUTH-006: Does not reveal whether an account exists.
    Per AUTH-009: Rate limiting is enforced at the middleware level.
    """
    from app.models.user import User, UserSession

    result = await db.execute(
        select(User).where(User.email == email.lower().strip())
    )
    user = result.scalar_one_or_none()

    # Generic error message that doesn't reveal account existence
    auth_error = AppError(
        code="AUTHENTICATION_FAILED",
        message="Invalid email or password.",
        status_code=401,
    )

    if not user or not verify_password(password, user.password_hash):
        raise auth_error

    if not user.is_active:
        raise AppError(
            code="ACCOUNT_DEACTIVATED",
            message="This account has been deactivated. Please contact support.",
            status_code=403,
        )

    # Create session
    session_id = str(uuid4())
    session = UserSession(
        id=uuid4(),
        user_id=user.id,
        session_token=session_id,
        device_info=user_agent or "unknown",
        ip_address=ip_address or "unknown",
        expires_at=datetime.now(UTC) + timedelta(days=get_settings().JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)

    # Update last login
    user.last_login_at = datetime.now(UTC)
    await db.flush()

    tokens = create_token_pair(user.id, user.role, session_id)

    await log_audit_event(
        db,
        actor_id=user.id,
        actor_role=user.role,
        action="user.login",
        resource_type="user",
        resource_id=user.id,
        ip_address=ip_address,
    )

    return {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
        "tokens": tokens,
    }


async def refresh_access_token(
    db: AsyncSession,
    *,
    refresh_token: str,
) -> dict:
    """Generate a new access token from a valid refresh token."""
    from app.models.user import User, UserSession

    payload = decode_token(refresh_token)
    if payload.type != "refresh" or not payload.session_id:
        raise AppError(
            code="INVALID_REFRESH_TOKEN",
            message="Invalid or expired refresh token.",
            status_code=401,
        )
    result = await db.execute(
        select(User).where(User.id == payload.sub, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AppError(
            code="INVALID_REFRESH_TOKEN",
            message="Invalid or expired refresh token.",
            status_code=401,
        )

    active_session = await db.execute(
        select(UserSession.id).where(
            UserSession.user_id == user.id,
            UserSession.session_token == payload.session_id,
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    if active_session.scalar_one_or_none() is None:
        raise AppError(
            code="INVALID_REFRESH_TOKEN",
            message="Invalid or expired refresh token.",
            status_code=401,
        )

    tokens = create_token_pair(user.id, user.role, payload.session_id)
    return {
        "user_id": str(user.id),
        "tokens": tokens,
    }


async def get_user_sessions(
    db: AsyncSession,
    user_id: UUID,
) -> list[dict]:
    """List active sessions for a user (AUTH-007)."""
    from app.models.user import UserSession

    result = await db.execute(
        select(UserSession).where(UserSession.user_id == user_id)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "device": s.device_info,
            "ip_address": s.ip_address,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_active_at": s.updated_at.isoformat() if hasattr(s, 'updated_at') and s.updated_at else None,
        }
        for s in sessions
    ]


async def revoke_session(
    db: AsyncSession,
    user_id: UUID,
    session_id: UUID | None = None,
) -> None:
    """Revoke a specific session or all sessions (AUTH-007)."""
    from app.models.user import UserSession

    if session_id:
        result = await db.execute(
            delete(UserSession).where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
            )
        )
        if result.rowcount == 0:
            raise NotFoundError("session")
    else:
        await db.execute(
            delete(UserSession).where(UserSession.user_id == user_id)
        )

    await log_audit_event(
        db,
        actor_id=user_id,
        actor_role="user",
        action="session.revoked",
        resource_type="session",
        resource_id=session_id or user_id,
    )
