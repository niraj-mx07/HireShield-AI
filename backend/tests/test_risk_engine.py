"""Tests for the weighted risk scoring engine."""

from __future__ import annotations

import pytest
from app.models.schemas import (
    CategoryResult,
    Recommendation,
    RiskBand,
    RiskCategory,
    RiskFactor,
    Severity,
)
from app.services.risk_engine import compute_confidence, score_assessment


def test_score_assessment_full_analyzed_low_risk():
    """Test full assessment with low risk across all categories."""
    results = {
        cat: CategoryResult(score=10.0, risk_factors=[], analyzed=True)
        for cat in RiskCategory
    }
    score, band, rec, confidence, category_scores, risk_factors = score_assessment(results)

    assert score == 10.0
    assert band == RiskBand.LOW
    assert rec == Recommendation.APPLY
    assert confidence == 1.0
    assert len(category_scores) == len(RiskCategory)


def test_score_assessment_dynamic_weight_normalization():
    """Test that when only job_content (weight 0.25) is analyzed with score 80.0,
    the normalized effective weight makes the risk score 80.0 instead of 20.0."""
    results = {
        RiskCategory.JOB_CONTENT: CategoryResult(score=80.0, risk_factors=[], analyzed=True),
        RiskCategory.URL_WEBSITE: CategoryResult(score=0.0, risk_factors=[], analyzed=False),
        RiskCategory.COMPANY_VERIFICATION: CategoryResult(score=0.0, risk_factors=[], analyzed=False),
    }

    score, band, rec, confidence, category_scores, risk_factors = score_assessment(results)

    # Effective weight of job content should be 1.0 (0.25 / 0.25)
    assert score == 80.0
    assert band in (RiskBand.HIGH, RiskBand.VERY_HIGH)
    assert rec == Recommendation.DONT_APPLY


def test_score_assessment_high_severity_floor():
    """Test that if any category produces a High severity risk factor, the overall score is at least 65.0."""
    high_rf = RiskFactor(
        category=RiskCategory.FINANCIAL_SCAM,
        severity=Severity.HIGH,
        description="Upfront fee requested.",
        evidence="Pay $200 processing fee",
        source="test",
        confidence=0.9,
    )
    results = {
        RiskCategory.FINANCIAL_SCAM: CategoryResult(score=30.0, risk_factors=[high_rf], analyzed=True),
    }

    score, band, rec, confidence, category_scores, risk_factors = score_assessment(results)

    assert score >= 65.0
    assert rec == Recommendation.DONT_APPLY


def test_compute_confidence_partial_coverage():
    """Test confidence computation when only some categories are analyzed."""
    results = {
        RiskCategory.JOB_CONTENT: CategoryResult(score=10.0, risk_factors=[], analyzed=True),
        RiskCategory.URL_WEBSITE: CategoryResult(score=10.0, risk_factors=[], analyzed=False),
    }

    conf = compute_confidence(results)
    assert 0.0 < conf < 1.0
