"""Tests for the URL and domain analysis module."""

from __future__ import annotations

import pytest
from app.analyzers import url_analysis
from app.models.schemas import Severity


@pytest.mark.asyncio
async def test_url_shortener_flagged():
    """Test URL shorteners like bit.ly trigger High severity risk factor."""
    result = await url_analysis.analyze(url="https://bit.ly/3xY1zAb")
    assert result.analyzed is True
    assert result.score >= 40.0
    assert any(rf.severity == Severity.HIGH for rf in result.risk_factors)
    assert any("shortener" in rf.description.lower() for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_free_hosting_flagged():
    """Test free hosts like webnode, wixsite, or google forms are flagged."""
    result = await url_analysis.analyze(url="https://forms.gle/xyz123abc")
    assert result.analyzed is True
    assert result.score >= 50.0
    assert any("free" in rf.description.lower() or "google form" in rf.description.lower() for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_mnc_brand_impersonation_flagged():
    """Test fake brand domain e.g., tcs-jobs-careers.com is flagged as impersonation."""
    result = await url_analysis.analyze(url="https://tcs-jobs-careers.com/apply")
    assert result.analyzed is True
    assert result.score >= 60.0
    assert any("impersonation" in rf.description.lower() for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_legitimate_mnc_url_low_risk():
    """Test genuine official MNC career portal has low risk."""
    result = await url_analysis.analyze(url="https://careers.google.com/jobs/results/123456")
    assert result.analyzed is True
    assert result.score < 30.0


@pytest.mark.asyncio
async def test_empty_url_unanalyzed():
    """Test empty URL returns analyzed=False."""
    result = await url_analysis.analyze(url="")
    assert result.analyzed is False
