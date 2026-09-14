"""Financial / Scam Signals — category weight 15 %.

Detects registration fees, deposits, payment requests, urgency language,
and other monetary red flags in job descriptions and communications.

This module is currently a **stub** that returns a neutral score.
"""

from __future__ import annotations

from app.models.schemas import CategoryResult, RiskCategory


async def analyze(
    description: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Scan text for financial and scam-pattern indicators.

    Args:
        description: Raw job description or communication text.

    Returns:
        A :class:`CategoryResult` — stub returns neutral score.
    """
    # TODO: Implement financial / scam signal detection
    #  - Registration fee / deposit requests
    #  - Advance payment demands
    #  - Urgency / pressure language patterns
    #  - "Guaranteed" income / unrealistic promises
    return CategoryResult(score=0.0, risk_factors=[], analyzed=False)
