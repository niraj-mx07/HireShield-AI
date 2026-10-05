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


@pytest.mark.asyncio
async def test_cashier_check_equipment_scam_flagged():
    """Cashier check home office reimbursement traps should produce high risk score."""
    check_text = (
        "We are hiring a Remote Executive Administrative Assistant at $42.50 per hour. "
        "Upon accepting our offer letter, our finance department will issue an official cashier's check "
        "of $4,200 for your certified Apple MacBook Pro and home office setup. You must deposit the check via "
        "mobile check deposit within 24 hours and wire the remaining funds to our certified equipment vendor."
    )
    result = await job_content.analyze(
        description=check_text,
        company_name="Vanguard Logistics Advisory",
    )
    assert result.analyzed is True
    assert result.score >= 50.0
    assert len(result.risk_factors) > 0


@pytest.mark.asyncio
async def test_telegram_rating_task_trap_flagged():
    """Prepaid YouTube / Google Maps rating tasks with daily payouts should produce high risk score."""
    task_text = (
        "Work from home part time. Watch and like YouTube videos and review restaurants on Google Maps. "
        "Earn ₹3,000 to ₹5,000 daily payout guaranteed via Google Pay or PhonePe. "
        "Connect directly on Telegram @maps_review_tasks to receive worker ID and recharge task balance."
    )
    result = await job_content.analyze(
        description=task_text,
        company_name="Social Media Promotions Hub",
    )
    assert result.analyzed is True
    assert result.score >= 50.0
    assert len(result.risk_factors) > 0


@pytest.mark.asyncio
async def test_legitimate_ai_startup_low_risk():
    """Legitimate tech startup posting with equity and tech stack should remain low risk."""
    startup_text = (
        "We are an applied AI startup building multimodal evaluation benchmarks. "
        "We are looking for a Senior Full Stack Engineer (FastAPI + React). "
        "Responsibilities: Build distributed data pipelines and clean user interfaces. "
        "Requirements: 4+ years Python, TypeScript, Docker, and PostgreSQL experience. "
        "We offer competitive salary, 0.5% equity, health insurance, and equipment stipend. "
        "Strict zero-fee recruitment policy. Apply on our official portal."
    )
    result = await job_content.analyze(
        description=startup_text,
        company_name="PromptEngine Labs",
    )
    assert result.analyzed is True
    assert result.score < 40.0
