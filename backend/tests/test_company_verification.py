"""Tests for company verification module."""

from __future__ import annotations

import pytest
from app.analyzers import company_verification
from app.models.schemas import Severity
from app.services import web_retrieval


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


# ---------------------------------------------------------------------------
# Live (consent-gated) listing-page verification
# ---------------------------------------------------------------------------


def _fake_page(payment_terms=None, has_job_posting=False):
    """Build a PageExtraction as the retrieval service would return it."""
    return web_retrieval.PageExtraction(
        url="https://careers-acme-groups.example.org/apply",
        final_url="https://careers-acme-groups.example.org/apply",
        domain="careers-acme-groups.example.org",
        status_code=200,
        text="Apply for the role.",
        has_job_posting=has_job_posting,
        payment_terms=payment_terms or [],
    )


@pytest.mark.asyncio
async def test_live_page_payment_prompt_raises_risk(monkeypatch):
    """A retrieved page soliciting payment produces a HIGH-severity factor."""
    async def fake_fetch(url, **kwargs):
        return _fake_page(payment_terms=["registration fee", "pay now", "upi"])

    monkeypatch.setattr(web_retrieval, "fetch_page", fake_fetch)

    result = await company_verification.analyze(
        company_name="Acme Recruiters Hub",
        url="https://careers-acme-groups.example.org/apply",
        consent=True,
    )

    assert result.analyzed is True
    assert result.score >= 60.0
    live = [rf for rf in result.risk_factors if rf.source == "live_careers_page_verifier"]
    assert live and live[0].severity == Severity.HIGH


@pytest.mark.asyncio
async def test_live_page_confirms_job_posting(monkeypatch):
    """A retrieved page with a real posting adds a LOW 'confirmed' factor."""
    async def fake_fetch(url, **kwargs):
        return _fake_page(has_job_posting=True)

    monkeypatch.setattr(web_retrieval, "fetch_page", fake_fetch)

    result = await company_verification.analyze(
        company_name="Acme Recruiters Hub",
        url="https://careers-acme-groups.example.org/apply",
        consent=True,
    )

    live = [rf for rf in result.risk_factors if rf.source == "live_careers_page_verifier"]
    assert live and live[0].severity == Severity.LOW


@pytest.mark.asyncio
async def test_live_page_unreachable_adds_medium_factor(monkeypatch):
    """A failed retrieval surfaces an inconclusive MEDIUM-severity factor."""
    async def fake_fetch(url, **kwargs):
        return None

    monkeypatch.setattr(web_retrieval, "fetch_page", fake_fetch)

    result = await company_verification.analyze(
        company_name="Acme Recruiters Hub",
        url="https://careers-acme-groups.example.org/apply",
        consent=True,
    )

    assert any(
        rf.source == "live_careers_page_verifier" and rf.severity == Severity.MEDIUM
        for rf in result.risk_factors
    )


@pytest.mark.asyncio
async def test_live_retrieval_requires_consent(monkeypatch):
    """Without consent the listing page is never fetched."""
    async def boom(*args, **kwargs):
        raise AssertionError("fetch_page must not run without consent")

    monkeypatch.setattr(web_retrieval, "fetch_page", boom)

    result = await company_verification.analyze(
        company_name="Acme Recruiters Hub",
        url="https://careers-acme-groups.example.org/apply",
        consent=False,
    )

    assert not any(rf.source == "live_careers_page_verifier" for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_live_retrieval_skips_trusted_job_boards(monkeypatch):
    """Trusted job boards already carry their own listing, so no fetch occurs."""
    async def boom(*args, **kwargs):
        raise AssertionError("trusted boards must not be re-fetched")

    monkeypatch.setattr(web_retrieval, "fetch_page", boom)

    result = await company_verification.analyze(
        company_name="Acme Recruiters Hub",
        url="https://www.linkedin.com/jobs/view/123456",
        consent=True,
    )

    assert not any(rf.source == "live_careers_page_verifier" for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_live_retrieval_reuses_pipeline_page(monkeypatch):
    """A page already fetched by the pipeline is reused, not re-fetched."""
    async def boom(*args, **kwargs):
        raise AssertionError("page was already supplied by the pipeline")

    monkeypatch.setattr(web_retrieval, "fetch_page", boom)

    result = await company_verification.analyze(
        company_name="Acme Recruiters Hub",
        url="https://careers-acme-groups.example.org/apply",
        consent=True,
        page_extraction=_fake_page(payment_terms=["pay now"]),
        page_attempted=True,
    )

    assert any(rf.source == "live_careers_page_verifier" for rf in result.risk_factors)

