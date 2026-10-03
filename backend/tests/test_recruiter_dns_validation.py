"""Tests for the DNS / MX validation rules in Recruiter Verification.

Rule 1 — no single-section contradictions.  A failed critical MX check pivots
         the whole Recruiter Verification section to FAIL and drops the
         positive "verified" evidence lines.
Rule 2 — strict DNS retry.  A lookup that cannot be completed is reported as
         "Network Timeout / Re-scan Required", never as "No MX records found".
Rule 3 — a confirmed zero-MX domain forces the overall verdict to DON'T APPLY.
"""

from __future__ import annotations

import httpx
import pytest

from app.analyzers import recruiter_verification as rv
from app.models.schemas import (
    CRITICAL_INFRA_FAILURE_SOURCE,
    CategoryResult,
    Recommendation,
    RiskBand,
    RiskCategory,
    RiskFactor,
    Severity,
)
from app.services import risk_engine


async def _no_mx(_domain):
    """Confirmed authoritative answer with zero MX records."""
    return rv.MxLookupResult(
        rv.MxLookupStatus.NO_RECORDS,
        attempts=1,
        detail="authoritative answer, 0 MX records",
    )


def _indeterminate(detail="ReadTimeout: the read operation timed out"):
    async def _inner(_domain):
        return rv.MxLookupResult(rv.MxLookupStatus.INDETERMINATE, attempts=3, detail=detail)

    return _inner


async def _found_mx(_domain):
    return rv.MxLookupResult(
        rv.MxLookupStatus.FOUND,
        records=("10 mail.acmecorp.example.",),
        attempts=1,
    )


# ---------------------------------------------------------------------------
# Rule 2 — enterprise DNS caching, retries, and honest failure reporting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mx_lookup_retries_after_timeouts(monkeypatch):
    """A flaky resolver is retried instead of being reported as 'no MX'."""
    calls = {"n": 0}

    async def flaky_dns(domain):
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ConnectTimeout("simulated resolver timeout")
        return {
            "Status": 0,
            "Answer": [{"name": domain, "type": 15, "data": "10 mail.example.com."}],
        }

    monkeypatch.setattr(rv, "_fetch_dns_json", flaky_dns)
    monkeypatch.setattr(rv, "_MX_BACKOFF_SECONDS", 0)

    result = await rv._check_domain_mx("example.com")
    assert result.status is rv.MxLookupStatus.FOUND
    assert result.attempts == 3
    assert calls["n"] == 3
    assert result.records


@pytest.mark.asyncio
async def test_persistent_timeout_is_indefinite_not_zero_records(monkeypatch):
    """After every retry fails, the answer is INDETERMINATE — not NO_RECORDS."""
    calls = {"n": 0}

    async def always_timeout(_domain):
        calls["n"] += 1
        raise httpx.ReadTimeout("simulated timeout")

    monkeypatch.setattr(rv, "_fetch_dns_json", always_timeout)
    monkeypatch.setattr(rv, "_MX_BACKOFF_SECONDS", 0)

    result = await rv._check_domain_mx("tcs.com")
    assert result.status is rv.MxLookupStatus.INDETERMINATE
    assert result.records == ()
    assert calls["n"] == rv._MX_ATTEMPTS


@pytest.mark.asyncio
async def test_servfail_is_retried_then_indefinite(monkeypatch):
    """SERVFAIL/REFUSED are resolver trouble, not proof of missing mail routing."""
    calls = {"n": 0}

    async def servfail(_domain):
        calls["n"] += 1
        return {"Status": 2, "Answer": []}

    monkeypatch.setattr(rv, "_fetch_dns_json", servfail)
    monkeypatch.setattr(rv, "_MX_BACKOFF_SECONDS", 0)

    result = await rv._check_domain_mx("google.com")
    assert result.status is rv.MxLookupStatus.INDETERMINATE
    assert calls["n"] == rv._MX_ATTEMPTS


@pytest.mark.asyncio
async def test_authoritative_empty_answer_is_zero_records(monkeypatch):
    """A NOERROR answer with no MX is an authoritative 'no mail routing'."""
    async def no_mx(_domain):
        return {"Status": 0, "Answer": []}

    monkeypatch.setattr(rv, "_fetch_dns_json", no_mx)
    result = await rv._check_domain_mx("brand-new-scam-domain.example")
    assert result.status is rv.MxLookupStatus.NO_RECORDS


@pytest.mark.asyncio
async def test_cname_answer_is_not_counted_as_an_mx_record(monkeypatch):
    """Only type-15 answers count as mail exchangers."""
    async def cname_only(domain):
        return {"Status": 0, "Answer": [{"name": domain, "type": 5, "data": "alias.example.com."}]}

    monkeypatch.setattr(rv, "_fetch_dns_json", cname_only)
    result = await rv._check_domain_mx("example.com")
    assert result.status is rv.MxLookupStatus.NO_RECORDS
    assert result.records == ()


def test_verified_enterprise_domain_matching():
    assert rv.is_verified_enterprise_domain("tcs.com") is True
    assert rv.is_verified_enterprise_domain("mail.google.com") is True
    assert rv.is_verified_enterprise_domain("MICROSOFT.COM") is True
    # Lookalike scam domains must not inherit enterprise leniency.
    assert rv.is_verified_enterprise_domain("tcs-jobs-careers.com") is False
    assert rv.is_verified_enterprise_domain("") is False


@pytest.mark.asyncio
async def test_fortune500_lookup_failure_reports_re_scan_not_missing_mx(monkeypatch):
    """Rule 2: a failed tcs.com lookup is a re-scan, never 'no MX records'."""
    monkeypatch.setattr(rv, "_check_domain_mx", _indeterminate())

    result = await rv.analyze(
        recruiter_email="recruiting@tcs.com",
        company_name="Tata Consultancy Services",
        consent=True,
    )
    assert result.analyzed is True
    assert not any(rf.severity == Severity.HIGH for rf in result.risk_factors)
    assert not any(rf.source == CRITICAL_INFRA_FAILURE_SOURCE for rf in result.risk_factors)

    re_scan = next(rf for rf in result.risk_factors if "re-scan" in rf.description.lower())
    assert re_scan.description == "Network Timeout / Re-scan Required"

    # Never claim the domain has no mail routing.
    assert not any("has no dns mx" in rf.description.lower() for rf in result.risk_factors)
    # A failed lookup alone must not pivot the section to FAIL.
    assert result.score < 60.0


@pytest.mark.asyncio
async def test_unknown_domain_lookup_failure_is_not_zero_mx(monkeypatch):
    """Rule 2 applies beyond the Fortune-500 list too."""
    monkeypatch.setattr(rv, "_check_domain_mx", _indeterminate("ConnectError: refused"))

    result = await rv.analyze(
        recruiter_email="hiring@small-firm-xyz.example",
        company_name="Small Firm XYZ",
        consent=True,
    )
    assert not any(rf.severity == Severity.HIGH for rf in result.risk_factors)
    assert not any(rf.source == CRITICAL_INFRA_FAILURE_SOURCE for rf in result.risk_factors)
    assert not any("has no dns mx" in rf.description.lower() for rf in result.risk_factors)


# ---------------------------------------------------------------------------
# Rule 1 — no single-section contradictions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mx_failure_pivots_section_to_fail_without_verified_evidence(monkeypatch):
    """Confirmed zero-MX: section FAILs and no 'verified' line survives."""
    monkeypatch.setattr(rv, "_check_domain_mx", _no_mx)

    result = await rv.analyze(
        recruiter_email="hiring@acmecorp.example",
        company_name="Acme Corp",
        consent=True,
    )

    # The whole section pivots to FAIL.
    assert result.score >= 60.0
    # One narrative only: no positive/"verified" line sits next to the failure.
    assert not any(rf.severity == Severity.LOW for rf in result.risk_factors)
    assert not any(rf.source == "corporate_email_verifier" for rf in result.risk_factors)
    assert not any(rf.source == "dns_mx_verifier" for rf in result.risk_factors)
    # The failure itself is critical, not a soft caution.
    assert any(
        rf.source == CRITICAL_INFRA_FAILURE_SOURCE and rf.severity == Severity.HIGH
        for rf in result.risk_factors
    )


@pytest.mark.asyncio
async def test_mx_success_keeps_corporate_match_evidence(monkeypatch):
    """Control: when MX resolves, the positive evidence line is preserved."""
    monkeypatch.setattr(rv, "_check_domain_mx", _found_mx)

    result = await rv.analyze(
        recruiter_email="hiring@acmecorp.example",
        company_name="Acme Corp",
        consent=True,
    )
    assert any(rf.source == "corporate_email_verifier" for rf in result.risk_factors)
    assert any(rf.source == "dns_mx_verifier" for rf in result.risk_factors)
    assert not any(rf.severity == Severity.HIGH for rf in result.risk_factors)
    assert result.score < 60.0


@pytest.mark.asyncio
async def test_mx_failure_plus_chat_channel_stays_coherent(monkeypatch):
    """Extra negative signals never resurrect a positive line after failure."""
    monkeypatch.setattr(rv, "_check_domain_mx", _no_mx)

    result = await rv.analyze(
        recruiter_email="hiring@acmecorp.example",
        company_name="Acme Corp",
        message="Contact our HR team on Telegram @Acme_HR immediately.",
        consent=True,
    )
    assert result.score >= 60.0
    assert not any(rf.severity == Severity.LOW for rf in result.risk_factors)
    assert not any(rf.source == "corporate_email_verifier" for rf in result.risk_factors)


# ---------------------------------------------------------------------------
# Rule 3 — final verdict override
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_confirmed_zero_mx_marks_critical_failure(monkeypatch):
    """A confirmed zero-MX domain carries the disqualifying source marker."""
    monkeypatch.setattr(rv, "_check_domain_mx", _no_mx)

    result = await rv.analyze(
        recruiter_email="hiring@fake-nonexistent-corp99.com",
        company_name="Fake Corp",
        consent=True,
    )
    assert result.score >= 60.0
    assert any(
        rf.source == CRITICAL_INFRA_FAILURE_SOURCE and rf.severity == Severity.HIGH
        for rf in result.risk_factors
    )


def test_risk_engine_forces_dont_apply_on_critical_failure():
    """Even a low band + no high severity cannot soften zero-MX into HOLD."""
    results = {
        RiskCategory.RECRUITER_VERIFICATION: CategoryResult(
            score=20.0,
            analyzed=True,
            risk_factors=[
                RiskFactor(
                    category=RiskCategory.RECRUITER_VERIFICATION,
                    # Deliberately not HIGH: the override alone must decide.
                    severity=Severity.MEDIUM,
                    description="Recruiter email domain has no DNS MX mail exchangers.",
                    source=CRITICAL_INFRA_FAILURE_SOURCE,
                    confidence=0.95,
                )
            ],
        )
    }

    score, band, rec, confidence, _, _ = risk_engine.score_assessment(results)
    assert rec is Recommendation.DONT_APPLY
    assert score >= 65.0
    assert band is not RiskBand.LOW


def test_risk_engine_without_critical_failure_is_unchanged():
    """Control: identical input with no confirmed failure keeps its verdict."""
    results = {
        RiskCategory.RECRUITER_VERIFICATION: CategoryResult(
            score=20.0,
            analyzed=True,
            risk_factors=[],
        )
    }

    score, band, rec, confidence, _, _ = risk_engine.score_assessment(results)
    assert score == 20.0
    assert band is RiskBand.LOW
    assert rec is Recommendation.APPLY
