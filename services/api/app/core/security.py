"""OAuth2 / JWT security utilities.

Provides token creation, validation, password hashing, and
FastAPI dependencies for extracting the current authenticated user.
"""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import bcrypt
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import Environment, get_settings
from app.core.database import get_db

settings = get_settings()

password_hasher = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


# ── Roles ────────────────────────────────────────────────────────────


class UserRole(StrEnum):
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
    type: Literal["access", "refresh"]

    @field_validator("sub")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        return str(UUID(value))


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ── Password utilities ───────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash a password with Argon2id, without bcrypt's 72-byte truncation."""
    return password_hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify current hashes and legacy bcrypt hashes during migration."""
    try:
        if hashed.startswith(("$2a$", "$2b$", "$2y$")):
            # Existing bcrypt accounts may contain historically truncated passwords.
            # Preserve that behavior only until their successful login rehashes them.
            return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("ascii"))
        return password_hasher.verify(hashed, plain)
    except (VerificationError, InvalidHashError, ValueError, UnicodeError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    return not hashed.startswith("$argon2") or password_hasher.check_needs_rehash(hashed)


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
        "aud": settings.JWT_AUDIENCE,
        "jti": str(uuid4()),
        "type": "access",
    }
    if session_id:
        claims["session_id"] = session_id
    if extra_claims:
        if set(extra_claims) & (set(claims) | {"session_id"}):
            raise ValueError("Extra claims cannot override security claims")
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
        "aud": settings.JWT_AUDIENCE,
        "jti": str(uuid4()),
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
            issuer=settings.OIDC_ISSUER_URL,
            audience=settings.JWT_AUDIENCE,
            options={
                "require": ["exp", "iat", "sub", "iss", "aud", "jti"],
            },
        )
        return TokenPayload(
            sub=payload["sub"],
            role=payload.get("role", "patient"),
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            jti=payload.get("jti"),
            session_id=payload.get("session_id"),
            type=payload["type"],
        )
    except (
        InvalidTokenError,
        ValidationError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        OSError,
    ) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ── FastAPI dependencies ─────────────────────────────────────────────


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> Any:
    """Extract and validate the current user from the JWT bearer token.

    Returns the User ORM instance. Raises 401 if invalid.
    """
    # Import here to avoid circular dependency
    from app.models.user import User, UserSession

    payload = decode_token(token)
    if payload.type != "access" or not payload.session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.sub

    result = await db.execute(
        select(User).where(
            User.id == UUID(user_id), User.is_active.is_(True), User.is_deleted.is_(False)
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    active_session = await db.execute(
        select(UserSession.id).where(
            UserSession.user_id == user.id,
            UserSession.session_token == payload.session_id,
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    if active_session.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or revoked",
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
    if (
        settings.ENVIRONMENT in {Environment.STAGING, Environment.PRODUCTION}
        and not current_user.is_verified
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account verification is required before accessing patient services.",
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
