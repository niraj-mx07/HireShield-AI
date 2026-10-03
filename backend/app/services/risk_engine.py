"""Weighted Risk-Scoring Engine.

Aggregates per-category scores into a single 0-100 risk score, derives a
risk band, recommendation, and overall confidence level.

Category weights (from README §Core Scoring and Intelligence Engine):

| Category                   | Weight |
|----------------------------|--------|
| Job Content Analysis       |  0.20  |
| Company Verification       |  0.20  |
| Recruiter Verification     |  0.15  |
| URL / Website Analysis     |  0.15  |
| Financial / Scam Signals   |  0.15  |
| Document Analysis          |  0.10  |
| Information Consistency    |  0.05  |

The weights sum to 1.0.
"""

from __future__ import annotations

from typing import Dict, List

from app.models.schemas import (
    CRITICAL_INFRA_FAILURE_SOURCE,
    CategoryResult,
    CategoryScore,
    Recommendation,
    RiskBand,
    RiskCategory,
    RiskFactor,
)

# Canonical weight mapping — single source of truth.
CATEGORY_WEIGHTS: Dict[RiskCategory, float] = {
    RiskCategory.JOB_CONTENT: 0.20,
    RiskCategory.COMPANY_VERIFICATION: 0.20,
    RiskCategory.RECRUITER_VERIFICATION: 0.15,
    RiskCategory.URL_WEBSITE: 0.15,
    RiskCategory.FINANCIAL_SCAM: 0.15,
    RiskCategory.DOCUMENT_ANALYSIS: 0.10,
    RiskCategory.INFORMATION_CONSISTENCY: 0.05,
}


def _risk_band(score: float) -> RiskBand:
    """Map a 0-100 score to its risk band.

    Thresholds (from README):
        0–30  → Low
        31–60 → Moderate
        61–80 → High
        81–100 → Very High
    """
    if score <= 30:
        return RiskBand.LOW
    if score <= 60:
        return RiskBand.MODERATE
    if score <= 80:
        return RiskBand.HIGH
    return RiskBand.VERY_HIGH


def _recommendation(
    band: RiskBand,
    confidence: float,
    max_severity: str | None = None,
    critical_failure: bool = False,
) -> Recommendation:
    """Derive a recommendation from risk band, confidence, and severity.

    ``critical_failure`` marks a positively confirmed absolute failure (e.g. a
    domain with zero MX records, which can neither send nor receive mail).
    Such a failure overrides every other consideration and is never softened
    into a HOLD.
    """
    # An absolute infrastructure failure is disqualifying on its own.
    if critical_failure:
        return Recommendation.DONT_APPLY

    # Critical high-severity scam indicators always warrant DONT_APPLY
    if band in (RiskBand.HIGH, RiskBand.VERY_HIGH) or max_severity == "high":
        return Recommendation.DONT_APPLY

    # Low evidence coverage on low risk -> advise caution (HOLD)
    if confidence < 0.35 and band == RiskBand.LOW:
        return Recommendation.HOLD

    if band == RiskBand.LOW:
        return Recommendation.APPLY
    if band == RiskBand.MODERATE:
        return Recommendation.HOLD

    return Recommendation.DONT_APPLY


def compute_confidence(results: Dict[RiskCategory, CategoryResult]) -> float:
    """Compute overall confidence from evidence coverage."""
    if not results:
        return 0.0

    analyzed_weight = sum(
        CATEGORY_WEIGHTS.get(cat, 0.0)
        for cat, result in results.items()
        if result.analyzed
    )
    total_weight = sum(CATEGORY_WEIGHTS.get(cat, 0.0) for cat in results)
    raw_ratio = analyzed_weight / total_weight if total_weight > 0 else 0.0
    # Map raw ratio [0.0 - 1.0] with base boost for having active analyzed fields
    return round(min(max(raw_ratio, 0.0), 1.0), 2)


def score_assessment(
    results: Dict[RiskCategory, CategoryResult],
) -> tuple[float, RiskBand, Recommendation, float, List[CategoryScore], List[RiskFactor]]:
    """Aggregate category results with dynamic weight normalization.

    When only a subset of inputs is provided by the user (e.g. only URL or only text),
    the active categories are dynamically normalized so that missing fields do not
    dilute confirmed risk signals.
    """
    category_scores: List[CategoryScore] = []
    all_risk_factors: List[RiskFactor] = []

    # 1. Calculate sum of weights for analyzed categories
    analyzed_weight_sum = sum(
        CATEGORY_WEIGHTS.get(cat, 0.0)
        for cat, res in results.items()
        if res.analyzed
    )

    total_weighted_score = 0.0
    has_high_severity = False

    for category, base_weight in CATEGORY_WEIGHTS.items():
        result = results.get(category, CategoryResult())
        
        # Determine normalized weight
        if result.analyzed and analyzed_weight_sum > 0:
            effective_weight = base_weight / analyzed_weight_sum
            weighted = result.score * effective_weight
            total_weighted_score += weighted
        else:
            effective_weight = base_weight
            weighted = 0.0

        for rf in result.risk_factors:
            if rf.severity.value == "high":
                has_high_severity = True

        category_scores.append(
            CategoryScore(
                category=category,
                score=result.score,
                weight=round(effective_weight, 3),
                weighted_score=round(weighted, 2),
                risk_factors=result.risk_factors,
                analyzed=result.analyzed,
            )
        )
        all_risk_factors.extend(result.risk_factors)

    risk_score = round(min(max(total_weighted_score, 0.0), 100.0), 2)
    
    # If high severity red flag exists, risk score should be at least high risk (65+)
    if has_high_severity and risk_score < 65.0:
        risk_score = 65.0

    # Rule: an absolute infrastructure failure (e.g. a domain confirmed to have
    # zero MX records) is disqualifying.  It raises the floor to the high-risk
    # band and forces DON'T APPLY rather than letting low confidence or a low
    # weighted score soften the verdict into HOLD.
    critical_failure = any(
        rf.source == CRITICAL_INFRA_FAILURE_SOURCE for rf in all_risk_factors
    )
    if critical_failure and risk_score < 65.0:
        risk_score = 65.0

    confidence = compute_confidence(results)
    band = _risk_band(risk_score)
    rec = _recommendation(
        band,
        confidence,
        max_severity="high" if has_high_severity else None,
        critical_failure=critical_failure,
    )

    return risk_score, band, rec, confidence, category_scores, all_risk_factors
