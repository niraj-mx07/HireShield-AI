"""Tests for assessment history listing and enhanced input summary."""

import pytest

from app.utils.privacy import build_input_summary


# ---------------------------------------------------------------------------
# build_input_summary — extended fields
# ---------------------------------------------------------------------------


def test_input_summary_with_all_fields():
    """Verify build_input_summary includes recruiter_phone and message metadata."""
    summary = build_input_summary(
        url="https://example.com/job",
        description="Senior engineer role",
        company_name="Example Corp",
        recruiter_email="hr@example.com",
        recruiter_name="Alice",
        recruiter_phone="+919876543210",
        message="Welcome to the team",
        has_document=True,
    )

    assert summary["url_provided"] is True
    assert summary["description_provided"] is True
    assert summary["description_length"] == len("Senior engineer role")
    assert summary["company_name_provided"] is True
    assert summary["recruiter_email_provided"] is True
    assert summary["recruiter_name_provided"] is True
    assert summary["recruiter_phone_provided"] is True
    assert summary["message_provided"] is True
    assert summary["message_length"] == len("Welcome to the team")
    assert summary["document_provided"] is True


def test_input_summary_optional_fields_none():
    """Verify new optional fields default to None/False when not provided."""
    summary = build_input_summary(url="https://example.com")

    assert summary["url_provided"] is True
    assert summary["recruiter_phone_provided"] is False
    assert summary["message_provided"] is False
    assert summary["message_length"] == 0
    assert summary["document_provided"] is False
