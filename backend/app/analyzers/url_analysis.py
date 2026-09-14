"""URL / Website Analysis — category weight 15 %.

Inspects HTTPS status, redirects, domain age/reputation, company-domain
mismatches, and classifies sources as official, third-party, or suspicious.

This module is currently a **stub** that returns a neutral score.
"""

from __future__ import annotations

from app.models.schemas import CategoryResult, RiskCategory


async def analyze(
    url: str | None = None,
    company_name: str | None = None,
    consent: bool = False,
    **kwargs,
) -> CategoryResult:
    """Analyse the submitted URL for domain and website risk indicators.

    Args:
        url: Job listing URL to inspect.
        company_name: Expected company name for domain-match checks.
        consent: Whether the user consented to external lookups.

    Returns:
        A :class:`CategoryResult` — stub returns neutral score.
    """
    # TODO: Implement URL / website analysis
    #  - HTTPS verification
    #  - Redirect chain inspection
    #  - Domain age / reputation lookup (requires consent)
    #  - Company-domain mismatch detection
    #  - Platform classification (official / third-party / suspicious)
    return CategoryResult(score=0.0, risk_factors=[], analyzed=False)
