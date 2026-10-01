"""Tests for PII redaction and community scam registry."""

from __future__ import annotations

import pytest
from app.utils.privacy import redact_pii


def test_pii_redaction_aadhaar_pan_ssn_card():
    """Verify Aadhaar, PAN, SSN, and Credit Cards are completely masked."""
    text = (
        "Applicant Aadhaar: 2345 6789 0123, PAN: ABCDE1234F, SSN: 123-45-6789. "
        "Paid via Card: 4111 2222 3333 4444. Contact: test@example.com, Phone: +91 9876543210."
    )
    redacted = redact_pii(text)
    assert "[AADHAAR_REDACTED]" in redacted
    assert "[PAN_REDACTED]" in redacted
    assert "[SSN_REDACTED]" in redacted
    assert "[CARD_REDACTED]" in redacted
    assert "[EMAIL_REDACTED]" in redacted
    assert "[PHONE_REDACTED]" in redacted
    assert "ABCDE1234F" not in redacted
    assert "2345 6789 0123" not in redacted
    assert "4111 2222 3333 4444" not in redacted
