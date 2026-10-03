"""Tests for the job-content classification policy.

Encodes the four classification rules enforced by
``app.analyzers.job_content`` / ``app.services.job_content_signals``:

1. Legal nouns and geographic indicators are neutral.
2. Brand names alone never raise risk ("brand poisoning" defence).
3. Only explicit deceptive mechanics escalate the score.
4. Corporate structure + explicit "no fee" defaults to SAFE (<15).
"""

from __future__ import annotations

import pytest

from app.analyzers import job_content
from app.models.schemas import RiskCategory, Severity
from app.services import job_content_signals
from app.services.model_loader import load_job_content_model


@pytest.fixture(autouse=True)
def ensure_model_loaded():
    """Ensure artifacts are loaded before tests run."""
    load_job_content_model()


# ---------------------------------------------------------------------------
# Rule 1 — legal nouns & geographic indicators are neutral
# ---------------------------------------------------------------------------

def test_neutralize_text_strips_legal_and_geo_terms():
    """Pvt/Ltd/Inc/Corp/India are removed before classification."""
    cleaned = job_content_signals.neutralize_text(
        "Acme Technologies Pvt Ltd Inc Corp India"
    )
    for token in ("pvt", "ltd", "inc", "corp", "india"):
        assert token not in cleaned.lower()


def test_neutralize_text_strips_brand_names():
    """Impersonated enterprise brands are removed before classification."""
    cleaned = job_content_signals.neutralize_text(
        "Tata Consultancy Services, TCS, Google and Amazon are hiring in India."
    )
    for token in ("tata", "tcs", "google", "amazon"):
        assert token not in cleaned.lower()


@pytest.mark.asyncio
async def test_legal_suffixes_and_geography_are_neutral():
    """A pure legal/geographic company label must not raise risk."""
    result = await job_content.analyze(
        company_name="Tata Consultancy Services Pvt Ltd India"
    )
    assert result.analyzed is True
    assert result.score < 30.0, f"Legal nouns raised risk to {result.score}"
    assert not any(rf.severity is Severity.HIGH for rf in result.risk_factors)


# ---------------------------------------------------------------------------
# Rule 2 — brand mentions are neutral on their own
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_brand_names_alone_do_not_raise_risk():
    """Listing several major brands must not be treated as a scam signal."""
    result = await job_content.analyze(
        description=(
            "We are Infosys, Wipro, TCS, Google and Amazon. "
            "Our offices are located in India."
        )
    )
    assert result.analyzed is True
    assert result.score < 30.0, f"Brand mentions raised risk to {result.score}"
    assert not any(rf.severity is Severity.HIGH for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_brand_plus_deceptive_pattern_still_flags():
    """A brand is neutral unless paired with an explicit deceptive mechanic."""
    result = await job_content.analyze(
        description=(
            "Google is hiring remote data entry staff. Pay a Rs 5000 registration "
            "fee to confirm your slot. Contact our Telegram supervisor @hr_google."
        )
    )
    assert result.analyzed is True
    assert result.score >= 65.0, f"Expected escalation, got {result.score}"
    assert any(rf.severity is Severity.HIGH for rf in result.risk_factors)


# ---------------------------------------------------------------------------
# Rule 3 — only explicit deceptive mechanics escalate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_fee_demand_escalates():
    """A pre-hiring fee demand is a high-severity mechanic."""
    result = await job_content.analyze(
        description=(
            "Work from home assistant needed immediately! Send $100 processing fee "
            "via wire transfer to secure your position."
        )
    )
    assert result.score >= 65.0
    assert any(
        rf.severity is Severity.HIGH and rf.source == "behavioral_advance_fee"
        for rf in result.risk_factors
    )
    assert all(rf.category is RiskCategory.JOB_CONTENT for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_fake_check_equipment_loop_escalates():
    """The 'we'll mail you a cheque to buy hardware' loop is flagged."""
    result = await job_content.analyze(
        description=(
            "We will mail you a check to buy hardware from our certified vendor "
            "portal before you start."
        )
    )
    assert result.score >= 65.0, f"Check loop scored only {result.score}"
    assert any(
        rf.severity is Severity.HIGH and rf.source == "behavioral_check_loop"
        for rf in result.risk_factors
    )


@pytest.mark.asyncio
async def test_unofficial_channel_escalates():
    """Interviewing exclusively via Telegram/WhatsApp is a high-severity mechanic."""
    result = await job_content.analyze(
        description=(
            "Interviews will be conducted entirely on Telegram. Contact @fast_jobs. "
            "No calls, no official email."
        )
    )
    assert result.score >= 65.0
    assert any(
        rf.severity is Severity.HIGH and rf.source == "behavioral_unofficial_channel"
        for rf in result.risk_factors
    )


@pytest.mark.asyncio
async def test_inflated_compensation_escalates():
    """Grossly inflated weekly pay for unskilled work is flagged."""
    result = await job_content.analyze(
        description=(
            "Entry level data entry job paying Rs 80000 per week, no skills required."
        )
    )
    assert result.score >= 65.0
    assert any(
        rf.severity is Severity.HIGH
        and rf.source == "behavioral_inflated_compensation"
        for rf in result.risk_factors
    )


# ---------------------------------------------------------------------------
# Rule 4 — corporate structure + explicit no-fee => SAFE
# ---------------------------------------------------------------------------

_CORPORATE_NO_FEE_TEXT = (
    "ACME Technologies Pvt Ltd India. Structured hiring process: online application, "
    "cognitive assessment, two technical interview rounds, and a standard background "
    "check. ACME never charges any recruitment fee, registration fee, security deposit, "
    "or training fee at any stage of the hiring process."
)


@pytest.mark.asyncio
async def test_corporate_structure_with_explicit_no_fee_is_safe():
    """Rule 4: standard process + 'no fee' statement defaults to SAFE (<15)."""
    result = await job_content.analyze(description=_CORPORATE_NO_FEE_TEXT)
    assert result.analyzed is True
    assert result.score < 15.0, f"Expected SAFE override, got {result.score}"
    assert any(
        rf.source == "contextual_no_fee_override" for rf in result.risk_factors
    )
    assert not any(rf.severity is Severity.HIGH for rf in result.risk_factors)


def test_negated_fee_is_not_a_demand():
    """'never charges any ... fee' must not become an advance-fee signal."""
    signals = job_content_signals.detect_behavioral_signals(_CORPORATE_NO_FEE_TEXT)
    assert not any(s.source == "behavioral_advance_fee" for s in signals)
    assert job_content_signals.has_explicit_no_fee(_CORPORATE_NO_FEE_TEXT) is True
    assert job_content_signals.has_corporate_structure(_CORPORATE_NO_FEE_TEXT) is True


def test_negation_does_not_unlock_real_demand():
    """A live payment instruction after 'no hidden charges' stays a demand."""
    signals = job_content_signals.detect_behavioral_signals(
        "No hidden charges, just pay the registration fee of Rs 5000 to confirm your slot."
    )
    assert any(s.source == "behavioral_advance_fee" for s in signals)


def test_empty_text_yields_no_signals():
    assert job_content_signals.detect_behavioral_signals("") == []
    assert job_content_signals.neutralize_text("") == ""

