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
# Aadhaar (12 digits, often formatted as 4-4-4)
_AADHAAR_RE = re.compile(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b")
# Indian PAN Card (5 uppercase letters, 4 digits, 1 uppercase letter)
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
# US Social Security Number (3-2-4 digits)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# Credit / Debit Cards (13 to 19 digits, optionally spaced or hyphenated)
_CARD_RE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")


def redact_pii(text: str) -> str:
    """Replace personal identifiers with redaction markers.

    Masks emails, phone numbers, Aadhaar numbers, PAN cards, SSNs, and credit cards.

    Args:
        text: Arbitrary string that may contain PII.

    Returns:
        A copy of *text* with sensitive identifiers safely replaced by redaction tags.
    """
    if not text:
        return ""
    result = _CARD_RE.sub("[CARD_REDACTED]", text)
    result = _AADHAAR_RE.sub("[AADHAAR_REDACTED]", result)
    result = _PAN_RE.sub("[PAN_REDACTED]", result)
    result = _SSN_RE.sub("[SSN_REDACTED]", result)
    result = _EMAIL_RE.sub("[EMAIL_REDACTED]", result)
    result = _PHONE_RE.sub("[PHONE_REDACTED]", result)
    return result




def build_input_summary(
    url: str | None = None,
    description: str | None = None,
    company_name: str | None = None,
    recruiter_email: str | None = None,
    recruiter_name: str | None = None,
    recruiter_phone: str | None = None,
    message: str | None = None,
    chat_transcript: str | None = None,
    message_log: str | None = None,
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
        "recruiter_phone_provided": recruiter_phone is not None,
        "message_provided": message is not None,
        "message_length": len(message) if message else 0,
        "chat_transcript_provided": chat_transcript is not None,
        "chat_transcript_length": len(chat_transcript) if chat_transcript else 0,
        "message_log_provided": message_log is not None,
        "message_log_length": len(message_log) if message_log else 0,
        "document_provided": has_document,
    }

