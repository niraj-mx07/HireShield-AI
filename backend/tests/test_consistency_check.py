"""Tests for cross-field consistency analyzer module."""

from __future__ import annotations

import pytest
from app.analyzers import consistency_check


@pytest.mark.asyncio
async def test_salary_role_mismatch():
    """Test recruiter email domain mismatch against company name triggers inconsistency flags."""
    result = await consistency_check.analyze(
        description="Simple copy-paste data entry work. Earn $5,000 per week guaranteed, no skills required.",
        company_name="Microsoft",
        recruiter_email="jobs@other-domain.com",
    )
    assert result.analyzed is True
    assert result.score >= 35.0
    assert any(rf.category.value == "information_consistency" for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_email_company_mismatch():
    """Test recruiter email domain mismatch with stated company name / URL."""
    result = await consistency_check.analyze(
        company_name="Microsoft",
        recruiter_email="jobs@amazon-careers-dept.com",
        url="https://microsoft.com/careers",
    )
    assert result.analyzed is True
    assert result.score >= 35.0
    assert any("conflict" in rf.description.lower() or "mismatch" in rf.description.lower() for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_empty_consistency_input_unanalyzed():
    """Test single or empty input returns analyzed=False."""
    result = await consistency_check.analyze(description="Single source input only")
    assert result.analyzed is False
