"""Tests for the financial signals risk analyzer."""

from __future__ import annotations

import pytest
from app.analyzers import financial_signals
from app.models.schemas import Severity


@pytest.mark.asyncio
async def test_upfront_payment_demand_flagged():
    """Test explicit requests for security deposits or training fees yield high risk."""
    desc = "Selected candidates must pay a refundable security deposit of Rs 2,500 for laptop allocation."
    result = await financial_signals.analyze(description=desc)
    assert result.analyzed is True
    assert result.score >= 40.0
    assert any(rf.severity == Severity.HIGH for rf in result.risk_factors)
    assert any("deposit" in rf.description.lower() or "fee" in rf.description.lower() or "payment" in rf.description.lower() for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_crypto_wire_payment_method_flagged():
    """Test cryptocurrency, USDT, or Western Union payment mentions trigger high severity."""
    msg = "We pay $50 per hour via USDT crypto wallet or Western Union wire transfer."
    result = await financial_signals.analyze(message=msg)
    assert result.analyzed is True
    assert result.score >= 35.0
    assert len(result.risk_factors) > 0


@pytest.mark.asyncio
async def test_normal_financial_terms_low_risk():
    """Test standard salary compensation mentions (e.g. CTC 8-10 LPA, direct bank deposit)."""
    desc = "Compensation: Rs 12,000,000 per annum + performance bonus. Standard direct bank transfer."
    result = await financial_signals.analyze(description=desc)
    assert result.analyzed is True
    assert result.score < 30.0


@pytest.mark.asyncio
async def test_empty_financial_input_unanalyzed():
    """Test empty financial inputs return analyzed=False."""
    result = await financial_signals.analyze(description=None, message=None)
    assert result.analyzed is False


@pytest.mark.asyncio
async def test_upi_vpa_handle_extracted():
    """Test explicit UPI VPA handles (e.g. hrfee@okaxis) are extracted and surfaced."""
    msg = "Send registration charge to hrrecruitment@okhdfcbank or 9812345678@paytm immediately."
    result = await financial_signals.analyze(message=msg)
    assert result.analyzed is True
    assert result.score >= 40.0
    assert any("hrrecruitment@okhdfcbank" in rf.evidence for rf in result.risk_factors)

