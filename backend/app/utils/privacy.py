"""PII redaction utilities for safe logging.

These helpers ensure that personal identifiers (emails, phone numbers) are
masked before any value reaches application logs, analytics, or error reports.

Usage::

    from app.utils.privacy import redact_pii

    logger.info("Processing input: %s", redact_pii(raw_text))
"""

from __future__ import annotations

import re


# Pre-compiled patterns for performance
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(
    r"(\+?\d{1,3}[-.\s]?)?"   # optional country code
    r"(\(?\d{2,4}\)?[-.\s]?)"  # area code
    r"(\d{3,4}[-.\s]?)"        # first group
    r"(\d{3,4})"               # second group
)


def redact_pii(text: str) -> str:
    """Replace email addresses and phone numbers with redaction markers.

    Args:
        text: Arbitrary string that may contain PII.

    Returns:
        A copy of *text* with emails replaced by ``[EMAIL_REDACTED]`` and
        phone numbers replaced by ``[PHONE_REDACTED]``.
    """
    result = _EMAIL_RE.sub("[EMAIL_REDACTED]", text)
    result = _PHONE_RE.sub("[PHONE_REDACTED]", result)
    return result


def build_input_summary(
    url: str | None = None,
    description: str | None = None,
    company_name: str | None = None,
    recruiter_email: str | None = None,
    recruiter_name: str | None = None,
    has_document: bool = False,
) -> dict:
    """Create a non-PII summary dict describing which inputs were provided.

    This is stored in the database instead of the raw inputs so that we
    retain auditability without persisting personal data.

    Returns:
        A dict like ``{"url_provided": True, "description_length": 423, ...}``.
    """
    return {
        "url_provided": url is not None,
        "description_provided": description is not None,
        "description_length": len(description) if description else 0,
        "company_name_provided": company_name is not None,
        "recruiter_email_provided": recruiter_email is not None,
        "recruiter_name_provided": recruiter_name is not None,
        "document_provided": has_document,
    }
