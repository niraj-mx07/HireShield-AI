"""Information Consistency — category weight 5 %.

Cross-checks data across the listing, email, document, and public sources
to detect contradictions (e.g., different company names, mismatched locations,
conflicting compensation figures).

This module is currently a **stub** that returns a neutral score.
"""

from __future__ import annotations

from app.models.schemas import CategoryResult, RiskCategory


async def analyze(
    description: str | None = None,
    url: str | None = None,
    company_name: str | None = None,
    recruiter_email: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Check for inconsistencies across submitted and verified information.

    Args:
        description: Job description text.
        url: Job listing URL.
        company_name: Stated company name.
        recruiter_email: Recruiter's email address.

    Returns:
        A :class:`CategoryResult` — stub returns neutral score.
    """
    # TODO: Implement consistency checking
    #  - Company name consistency across sources
    #  - Location / compensation conflicts
    #  - Timeline inconsistencies
    return CategoryResult(score=0.0, risk_factors=[], analyzed=False)
