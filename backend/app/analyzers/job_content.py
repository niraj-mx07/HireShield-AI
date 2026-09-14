"""Job Content Analysis — category weight 20 %.

Detects vague role scope, unrealistic salary promises, missing employer
details, and other content-level red flags in the job description.

This module is currently a **stub** that returns a neutral score.
Real implementation will use NLP/ML models (spaCy, Hugging Face).
"""

from __future__ import annotations

from app.models.schemas import CategoryResult, RiskCategory


async def analyze(
    description: str | None = None,
    company_name: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Analyse job-posting content for risk indicators.

    Args:
        description: Raw job description text.
        company_name: Name of the hiring company/organisation.

    Returns:
        A :class:`CategoryResult` with score, risk factors, and
        ``analyzed=False`` while this is a stub.
    """
    # TODO: Implement NLP-based content analysis
    #  - Vague role scope detection
    #  - Salary / compensation reasonableness check
    #  - Missing employer details
    #  - Urgency language detection
    return CategoryResult(score=0.0, risk_factors=[], analyzed=False)
