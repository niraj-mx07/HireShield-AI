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


def _recommendation(band: RiskBand, confidence: float) -> Recommendation:
    """Derive a recommendation from risk band and confidence.

    Per README: "Missing evidence reduces confidence and can result in HOLD
    even when the score is below a rejection threshold."
    """
    if confidence < 0.3:
        # Very low evidence coverage → always HOLD regardless of score.
        return Recommendation.HOLD

    if band == RiskBand.LOW:
        return Recommendation.APPLY
    if band == RiskBand.MODERATE:
        return Recommendation.HOLD
    # HIGH or VERY_HIGH
    return Recommendation.DONT_APPLY


def compute_confidence(results: Dict[RiskCategory, CategoryResult]) -> float:
    """Compute overall confidence from evidence coverage.

    Confidence is the weighted fraction of categories where real analysis
    was performed (``analyzed=True``).  Categories with higher weights
    contribute more to the confidence value.

    Returns:
        A value in [0.0, 1.0].
    """
    if not results:
        return 0.0

    analyzed_weight = sum(
        CATEGORY_WEIGHTS.get(cat, 0.0)
        for cat, result in results.items()
        if result.analyzed
    )
    total_weight = sum(CATEGORY_WEIGHTS.get(cat, 0.0) for cat in results)
    return analyzed_weight / total_weight if total_weight > 0 else 0.0


def score_assessment(
    results: Dict[RiskCategory, CategoryResult],
) -> tuple[float, RiskBand, Recommendation, float, List[CategoryScore], List[RiskFactor]]:
    """Aggregate category results into the final risk assessment.

    Args:
        results: Mapping of each :class:`RiskCategory` to its
            :class:`CategoryResult` (from an analyzer module).

    Returns:
        A tuple of ``(risk_score, risk_band, recommendation, confidence,
        category_scores, all_risk_factors)``.
    """
    category_scores: List[CategoryScore] = []
    all_risk_factors: List[RiskFactor] = []
    total_weighted_score = 0.0

    for category, weight in CATEGORY_WEIGHTS.items():
        result = results.get(category, CategoryResult())
        weighted = result.score * weight
        total_weighted_score += weighted

        category_scores.append(
            CategoryScore(
                category=category,
                score=result.score,
                weight=weight,
                weighted_score=round(weighted, 2),
                risk_factors=result.risk_factors,
                analyzed=result.analyzed,
            )
        )
        all_risk_factors.extend(result.risk_factors)

    risk_score = round(min(max(total_weighted_score, 0.0), 100.0), 2)
    confidence = compute_confidence(results)
    band = _risk_band(risk_score)
    rec = _recommendation(band, confidence)

    return risk_score, band, rec, round(confidence, 2), category_scores, all_risk_factors
