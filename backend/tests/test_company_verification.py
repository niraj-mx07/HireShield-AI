"""Tests for company verification module."""

from __future__ import annotations

import pytest
from app.analyzers import company_verification


@pytest.mark.asyncio
async def test_high_risk_generic_company_name():
    """Test generic high-risk shell company names like 'Global Data Entry Solutions Pvt Ltd'."""
    result = await company_verification.analyze(
        company_name="Global Fast Data Entry Services Ltd",
        description="Data entry typists needed urgently",
    )
    assert result.analyzed is True
    assert result.score >= 35.0
    assert len(result.risk_factors) > 0


@pytest.mark.asyncio
async def test_established_reputable_company_name():
    """Test recognized Fortune 500 / Indian IT major company names with official domain."""
    result = await company_verification.analyze(
        company_name="Tata Consultancy Services",
        url="https://tcs.com/careers/job-123",
    )
    assert result.analyzed is True
    assert result.score < 25.0


@pytest.mark.asyncio
async def test_empty_company_name_unanalyzed():
    """Test empty company name returns analyzed=False."""
    result = await company_verification.analyze(company_name="", url="")
    assert result.analyzed is False


@pytest.mark.asyncio
async def test_newly_added_enterprise_verified():
    """Test newly added enterprises like Accenture and Deloitte are verified."""
    result = await company_verification.analyze(
        company_name="Accenture",
        url="https://accenture.com/careers/job-456",
    )
    assert result.analyzed is True
    assert result.score < 20.0
    assert any("verified" in rf.description.lower() for rf in result.risk_factors)

