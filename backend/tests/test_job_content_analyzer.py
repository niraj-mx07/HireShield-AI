"""Tests for the job content ML analyzer module."""

from __future__ import annotations

import pytest

from app.analyzers import job_content
from app.models.schemas import RiskCategory, Severity
from app.services.model_loader import load_job_content_model


@pytest.fixture(autouse=True)
def ensure_model_loaded():
    """Ensure artifacts are loaded before tests run."""
    load_job_content_model()


@pytest.mark.asyncio
async def test_fraudulent_job_posting_high_risk():
    """An obviously fraudulent posting should yield an elevated risk score."""
    fraud_description = (
        "URGENT HIRING: Work from home personal assistant needed immediately! "
        "No experience required! Earn $5000 weekly guaranteed. Send $100 processing fee "
        "via wire transfer or Western Union to secure your position and receive your starter kit today."
    )

    result = await job_content.analyze(
        description=fraud_description,
        company_name="Global Fast Cash Logistics",
    )

    assert result.analyzed is True
    assert result.score >= 50.0, f"Expected elevated risk score for scam text, got {result.score}"
    assert len(result.risk_factors) > 0
    assert result.risk_factors[0].category == RiskCategory.JOB_CONTENT
    assert result.risk_factors[0].severity in (Severity.HIGH, Severity.MEDIUM)


@pytest.mark.asyncio
async def test_legitimate_job_posting_low_risk():
    """An obviously legitimate job posting should produce a lower risk score."""
    normal_description = (
        "We are looking for a Senior Software Engineer to join our team at Google. "
        "Responsibilities include designing distributed systems, mentoring junior developers, "
        "and collaborating with cross-functional teams. Requirements: Bachelor's degree in Computer "
        "Science or equivalent practical experience, 5+ years writing production Python, and familiarity "
        "with cloud infrastructure. We offer comprehensive health benefits, 401(k) matching, and equity."
    )

    result = await job_content.analyze(
        description=normal_description,
        company_name="Google",
    )

    assert result.analyzed is True
    assert result.score < 45.0, f"Expected low/moderate score for legitimate posting, got {result.score}"


@pytest.mark.asyncio
async def test_empty_input_returns_unanalyzed():
    """Passing no text or whitespace should gracefully return analyzed=False."""
    result = await job_content.analyze(description=None, company_name=None)
    assert result.analyzed is False
    assert result.score == 0.0
    assert len(result.risk_factors) == 0

    result_whitespace = await job_content.analyze(description="   ", company_name="")
    assert result_whitespace.analyzed is False
