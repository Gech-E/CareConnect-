"""Structured JSON logging with PHI redaction.

Per SRS §10.4: logs must be structured JSON, include request/correlation
IDs, and must NOT contain access tokens, passwords, message bodies,
diagnosis, medication names, document contents, or full patient identifiers.
"""

import logging
import sys
from typing import Any

import structlog

# Fields that must NEVER appear in logs (PHI/secrets)
REDACTED_FIELDS = frozenset({
    "password",
    "password_hash",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "ssn",
    "social_security",
    "diagnosis",
    "medication_name",
    "message_body",
    "body",
    "instructions",
    "content_hash",
    "secret",
    "credit_card",
})


def redact_sensitive_fields(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that redacts PHI and secrets from log entries."""
    for key in list(event_dict.keys()):
        if key.lower() in REDACTED_FIELDS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            redact_sensitive_fields,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
