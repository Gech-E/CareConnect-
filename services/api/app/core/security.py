"""OAuth2 / JWT security utilities.

Provides token creation, validation, password hashing, and
FastAPI dependencies for extracting the current authenticated user.
"""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_settings
from app.core.database import get_db

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


# ── Roles ────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    """System roles per SRS §3.1."""

    PATIENT = "patient"
    CLINICIAN = "clinician"
    CLINICAL_STAFF = "clinical_staff"
    SUPPORT = "support"
    ADMIN = "admin"
    AUDITOR = "auditor"
    SYSTEM = "system"


# ── Token models ─────────────────────────────────────────────────────

class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: datetime
    iat: datetime
    jti: str | None = None
    session_id: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ── Password utilities ───────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


# ── Token creation ───────────────────────────────────────────────────

def create_access_token(
    subject: str | UUID,
    role: str,
    session_id: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    claims: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": expire,
        "iss": settings.OIDC_ISSUER_URL,
        "type": "access",
    }
    if session_id:
        claims["session_id"] = session_id
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str | UUID,
    session_id: str | None = None,
) -> str:
    """Create a long-lived JWT refresh token."""
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    claims: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "iss": settings.OIDC_ISSUER_URL,
        "type": "refresh",
    }
    if session_id:
        claims["session_id"] = session_id
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_token_pair(
    subject: str | UUID,
    role: str,
    session_id: str | None = None,
) -> TokenPair:
    """Create an access + refresh token pair."""
    return TokenPair(
        access_token=create_access_token(subject, role, session_id),
        refresh_token=create_refresh_token(subject, session_id),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Token validation ────────────────────────────────────────────────

def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token.

    Raises HTTPException on invalid or expired tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return TokenPayload(
            sub=payload["sub"],
            role=payload.get("role", "patient"),
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            jti=payload.get("jti"),
            session_id=payload.get("session_id"),
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ── FastAPI dependencies ─────────────────────────────────────────────

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Extract and validate the current user from the JWT bearer token.

    Returns the User ORM instance. Raises 401 if invalid.
    """
    # Import here to avoid circular dependency
    from app.models.user import User

    payload = decode_token(token)
    user_id = payload.sub

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: Annotated[Any, Depends(get_current_user)],
) -> Any:
    """Ensure the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return current_user


def require_roles(*roles: UserRole):
    """Factory that returns a dependency enforcing role membership.

    Usage::

        @router.get("/admin/users", dependencies=[Depends(require_roles(UserRole.ADMIN))])
    """

    async def _check(current_user: Annotated[Any, Depends(get_current_active_user)]) -> Any:
        if current_user.role not in [r.value for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check
