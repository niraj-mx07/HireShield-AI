"""Tests for recruiter verification module."""

from __future__ import annotations

import pytest
from app.analyzers import recruiter_verification
from app.models.schemas import Severity


@pytest.mark.asyncio
async def test_free_email_domain_for_recruiter():
    """Test recruiter using gmail/yahoo/hotmail is flagged."""
    result = await recruiter_verification.analyze(
        recruiter_email="hr.careers.google@gmail.com",
        company_name="Google",
    )
    assert result.analyzed is True
    assert result.score >= 50.0
    assert any(rf.severity == Severity.HIGH for rf in result.risk_factors)
    assert any("webmail" in rf.description.lower() or "free email" in rf.description.lower() for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_telegram_whatsapp_only_contact():
    """Test recruiter directing communication only to Telegram or WhatsApp."""
    msg = "Contact our HR team on Telegram @HR_Recruiter_Dept or WhatsApp +91-9999999999 immediately."
    result = await recruiter_verification.analyze(message=msg)
    assert result.analyzed is True
    assert result.score >= 40.0
    assert any("chat" in rf.description.lower() or "telegram" in rf.description.lower() for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_corporate_email_matching_company():
    """Test verified corporate email matching official domain."""
    result = await recruiter_verification.analyze(
        recruiter_email="recruiting@google.com",
        company_name="Google",
    )
    assert result.analyzed is True
    assert result.score < 25.0


@pytest.mark.asyncio
async def test_no_recruiter_info_unanalyzed():
    """Test empty recruiter info returns analyzed=False."""
    result = await recruiter_verification.analyze(recruiter_email=None, recruiter_name="", message=None)
    assert result.analyzed is False
