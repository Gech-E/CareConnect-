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
REDACTED_FIELDS = frozenset(
    {
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
        "email",
        "phone",
        "date_of_birth",
        "cookie",
        "set-cookie",
        "exc_info",
        "exception",
        "stack_info",
    }
)


class ExceptionPrivacyFilter(logging.Filter):
    """Uvicorn re-logs handled ASGI errors; omit their potentially sensitive text."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exception_type = record.exc_info[0]
            record.msg = "Unhandled ASGI error (%s); see correlated application event"
            record.args = (exception_type.__name__ if exception_type else "Exception",)
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


def redact_sensitive_fields(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that redacts PHI and secrets from log entries."""

    def redact(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if str(key).lower() in REDACTED_FIELDS else redact(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [redact(item) for item in value]
        return value

    return redact(event_dict)


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
    server_logger = logging.getLogger("uvicorn.error")
    if not any(isinstance(item, ExceptionPrivacyFilter) for item in server_logger.filters):
        server_logger.addFilter(ExceptionPrivacyFilter())
