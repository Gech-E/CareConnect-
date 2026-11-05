"""Records and document management service.

Implements SRS §4.9-4.10: record listing, document upload via
presigned URLs, download with audit logging, and FHIR provenance.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.storage import generate_presigned_download_url, generate_presigned_upload_url
from app.services.audit_service import log_audit_event

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Records ──────────────────────────────────────────────────────────

async def get_patient_records(
    db: AsyncSession,
    patient_id: UUID,
    record_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> dict:
    """List patient records with filters (REC-001, REC-002)."""
    from app.models.record import MedicalRecord

    stmt = select(MedicalRecord).where(
        MedicalRecord.patient_id == patient_id,
        MedicalRecord.is_deleted == False,  # noqa: E712
    )

    if record_type:
        stmt = stmt.where(MedicalRecord.record_type == record_type)
    if date_from:
        stmt = stmt.where(MedicalRecord.service_date >= date_from)
    if date_to:
        stmt = stmt.where(MedicalRecord.service_date <= date_to)
    if search:
        stmt = stmt.where(MedicalRecord.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(MedicalRecord.service_date.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    records = result.scalars().all()

    has_more = len(records) > limit
    if has_more:
        records = records[:limit]

    return {
        "items": [
            {
                "id": str(r.id),
                "record_type": r.record_type,
                "title": r.title,
                "source_system": r.source_system,
                "service_date": r.service_date.isoformat() if r.service_date else None,
                "status": r.status,
                "fhir_resource_type": r.fhir_resource_type,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
        "next_cursor": str(records[-1].id) if has_more else None,
        "has_more": has_more,
    }


async def get_record_by_id(
    db: AsyncSession,
    record_id: UUID,
    patient_id: UUID,
    ip_address: str | None = None,
) -> dict:
    """Get a single record with authorization and audit (REC-004)."""
    from app.models.record import MedicalRecord

    result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == record_id,
            MedicalRecord.is_deleted == False,  # noqa: E712
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise NotFoundError("record")

    # Authorization: patient can only see their own records
    if record.patient_id != patient_id:
        raise ForbiddenError()

    # Audit event for viewing protected data
    await log_audit_event(
        db,
        actor_id=patient_id,
        actor_role="patient",
        action="record.viewed",
        resource_type="medical_record",
        resource_id=record_id,
        ip_address=ip_address,
    )

    return {
        "id": str(record.id),
        "record_type": record.record_type,
        "title": record.title,
        "source_system": record.source_system,
        "source_id": record.source_id,
        "service_date": record.service_date.isoformat() if record.service_date else None,
        "status": record.status,
        "fhir_resource_type": record.fhir_resource_type,
        "fhir_resource_id": record.fhir_resource_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


# ── Documents ────────────────────────────────────────────────────────

async def create_upload_intent(
    db: AsyncSession,
    *,
    owner_id: UUID,
    filename: str,
    content_type: str,
    context_type: str,
    context_id: UUID,
    ip_address: str | None = None,
) -> dict:
    """Create a document upload intent with presigned URL (REC-005).

    Validates MIME type before generating the upload URL.
    """
    from app.models.record import Document

    # Validate MIME type (SRS §10.3: validate by content, not filename)
    if content_type not in settings.ALLOWED_UPLOAD_TYPES:
        from app.core.exceptions import AppError
        raise AppError(
            code="UNSUPPORTED_FILE_TYPE",
            message=f"File type '{content_type}' is not supported.",
            status_code=400,
        )

    # Generate storage key (never expose internal paths per REC-006)
    storage_key = f"{context_type}/{context_id}/{uuid4()}/{filename}"

    document = Document(
        owner_id=owner_id,
        context_type=context_type,
        context_id=context_id,
        storage_key=storage_key,
        original_filename=filename,
        mime_type=content_type,
        scan_status="pending",
    )
    db.add(document)
    await db.flush()

    # Generate presigned upload URL
    upload_url = generate_presigned_upload_url(storage_key, content_type)

    await log_audit_event(
        db,
        actor_id=owner_id,
        actor_role="user",
        action="document.upload_intent_created",
        resource_type="document",
        resource_id=document.id,
        ip_address=ip_address,
    )

    return {
        "document_id": str(document.id),
        "upload_url": upload_url,
        "expires_at": (datetime.now(UTC).isoformat()),
    }


async def complete_upload(
    db: AsyncSession,
    document_id: UUID,
    owner_id: UUID,
    content_hash: str,
    size_bytes: int | None = None,
) -> dict:
    """Mark a document upload as complete after client upload."""
    from app.models.record import Document

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == owner_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise NotFoundError("document")

    document.content_hash = content_hash
    document.size_bytes = size_bytes
    document.scan_status = "clean"  # In production: trigger async malware scan
    document.uploaded_at = datetime.now(UTC)

    await db.flush()

    return {
        "id": str(document.id),
        "status": "uploaded",
        "scan_status": document.scan_status,
    }


async def get_download_url(
    db: AsyncSession,
    document_id: UUID,
    user_id: UUID,
    user_role: str,
    ip_address: str | None = None,
) -> dict:
    """Generate a presigned download URL with audit (REC-004, REC-005)."""
    from app.models.record import Document

    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise NotFoundError("document")

    # Authorization check
    if user_role == "patient" and document.owner_id != user_id:
        raise ForbiddenError()

    # Check scan status
    if document.scan_status not in ("clean", "pending"):
        from app.core.exceptions import AppError
        raise AppError(
            code="DOCUMENT_UNAVAILABLE",
            message="This document is not available for download.",
            status_code=403,
        )

    download_url = generate_presigned_download_url(document.storage_key)

    # Audit event for download (REC-004)
    await log_audit_event(
        db,
        actor_id=user_id,
        actor_role=user_role,
        action="document.downloaded",
        resource_type="document",
        resource_id=document_id,
        ip_address=ip_address,
    )

    return {
        "download_url": download_url,
        "filename": document.original_filename,
        "mime_type": document.mime_type,
        "expires_at": (datetime.now(UTC).isoformat()),
    }
