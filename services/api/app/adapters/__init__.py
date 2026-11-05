"""Integration adapters for external services.

Per SRS §8: All external services use adapter interfaces with
local mock implementations for development. Never require real
vendor credentials to run locally.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


# ── Video Provider Adapter ───────────────────────────────────────────

class VideoProviderAdapter(ABC):
    """Abstract video provider interface (SRS §8.2)."""

    @abstractmethod
    async def create_session(self, appointment_id: UUID) -> dict:
        """Create a video session/room."""
        ...

    @abstractmethod
    async def generate_token(
        self, session_id: str, participant_id: UUID, role: str
    ) -> dict:
        """Generate a participant-scoped, short-lived token."""
        ...

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        """End a video session."""
        ...


class MockVideoProvider(VideoProviderAdapter):
    """Mock video provider for local development."""

    async def create_session(self, appointment_id: UUID) -> dict:
        session_id = f"mock-room-{uuid4().hex[:12]}"
        logger.info("mock_video.session_created", session_id=session_id)
        return {"session_id": session_id, "provider": "mock"}

    async def generate_token(
        self, session_id: str, participant_id: UUID, role: str
    ) -> dict:
        token = f"mock-token-{uuid4().hex[:24]}"
        logger.info("mock_video.token_generated", session_id=session_id)
        return {"token": token, "expires_in": 3600}

    async def end_session(self, session_id: str) -> None:
        logger.info("mock_video.session_ended", session_id=session_id)


# ── Notification Adapter ────────────────────────────────────────────

class NotificationAdapter(ABC):
    """Abstract notification interface (SRS §8.3)."""

    @abstractmethod
    async def send_email(
        self, to: str, subject: str, body: str, template_key: str | None = None
    ) -> dict:
        ...

    @abstractmethod
    async def send_sms(self, to: str, body: str) -> dict:
        ...

    @abstractmethod
    async def send_push(
        self, device_token: str, title: str, body: str
    ) -> dict:
        ...


class MockNotificationAdapter(NotificationAdapter):
    """Mock notification adapter — logs all notifications."""

    async def send_email(
        self, to: str, subject: str, body: str, template_key: str | None = None
    ) -> dict:
        logger.info(
            "mock_notification.email_sent",
            to=to,
            subject=subject,
            template=template_key,
        )
        return {"id": str(uuid4()), "status": "sent", "channel": "email"}

    async def send_sms(self, to: str, body: str) -> dict:
        logger.info("mock_notification.sms_sent", to=to)
        return {"id": str(uuid4()), "status": "sent", "channel": "sms"}

    async def send_push(
        self, device_token: str, title: str, body: str
    ) -> dict:
        logger.info("mock_notification.push_sent", title=title)
        return {"id": str(uuid4()), "status": "sent", "channel": "push"}


# ── FHIR/EHR Adapter ────────────────────────────────────────────────

class FHIRAdapter(ABC):
    """Abstract FHIR R4 adapter (SRS §8.4)."""

    @abstractmethod
    async def get_patient(self, patient_id: str) -> dict:
        ...

    @abstractmethod
    async def get_appointments(self, patient_id: str) -> list[dict]:
        ...

    @abstractmethod
    async def create_encounter(self, encounter_data: dict) -> dict:
        ...

    @abstractmethod
    async def get_medication_requests(self, patient_id: str) -> list[dict]:
        ...

    @abstractmethod
    async def get_diagnostic_reports(self, patient_id: str) -> list[dict]:
        ...


class MockFHIRAdapter(FHIRAdapter):
    """Mock FHIR adapter returning synthetic data."""

    async def get_patient(self, patient_id: str) -> dict:
        return {
            "resourceType": "Patient",
            "id": patient_id,
            "name": [{"family": "Johnson", "given": ["Maya"]}],
            "gender": "female",
            "birthDate": "1990-03-15",
        }

    async def get_appointments(self, patient_id: str) -> list[dict]:
        return []

    async def create_encounter(self, encounter_data: dict) -> dict:
        return {
            "resourceType": "Encounter",
            "id": str(uuid4()),
            "status": "finished",
        }

    async def get_medication_requests(self, patient_id: str) -> list[dict]:
        return []

    async def get_diagnostic_reports(self, patient_id: str) -> list[dict]:
        return []


# ── Pharmacy Adapter ────────────────────────────────────────────────

class PharmacyAdapter(ABC):
    """Abstract pharmacy/fulfillment adapter (SRS §8.5)."""

    @abstractmethod
    async def get_pharmacies(self, zip_code: str) -> list[dict]:
        ...

    @abstractmethod
    async def submit_fulfillment(
        self, prescription_id: str, pharmacy_id: str, delivery_method: str
    ) -> dict:
        ...

    @abstractmethod
    async def check_fulfillment_status(self, reference_id: str) -> dict:
        ...


class MockPharmacyAdapter(PharmacyAdapter):
    """Mock pharmacy adapter for development."""

    async def get_pharmacies(self, zip_code: str) -> list[dict]:
        return [
            {
                "id": "pharm-001",
                "name": "CareConnect Pharmacy - Downtown",
                "address": "123 Health St, Suite 100",
                "phone": "(555) 123-4567",
                "hours": "Mon-Fri 8am-8pm",
                "delivery_available": True,
            },
            {
                "id": "pharm-002",
                "name": "CareConnect Pharmacy - Westside",
                "address": "456 Wellness Ave",
                "phone": "(555) 987-6543",
                "hours": "Mon-Sat 9am-9pm",
                "delivery_available": False,
            },
        ]

    async def submit_fulfillment(
        self, prescription_id: str, pharmacy_id: str, delivery_method: str
    ) -> dict:
        return {
            "reference_id": f"mock-ful-{uuid4().hex[:8]}",
            "status": "accepted",
            "estimated_ready": "2-4 hours",
        }

    async def check_fulfillment_status(self, reference_id: str) -> dict:
        return {"reference_id": reference_id, "status": "processing"}


# ── Adapter factory ─────────────────────────────────────────────────

def get_video_provider() -> VideoProviderAdapter:
    """Return the configured video provider adapter."""
    return MockVideoProvider()


def get_notification_adapter() -> NotificationAdapter:
    """Return the configured notification adapter."""
    return MockNotificationAdapter()


def get_fhir_adapter() -> FHIRAdapter:
    """Return the configured FHIR adapter."""
    return MockFHIRAdapter()


def get_pharmacy_adapter() -> PharmacyAdapter:
    """Return the configured pharmacy adapter."""
    return MockPharmacyAdapter()
