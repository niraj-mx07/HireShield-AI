"""Company Verification — category weight 20 %.

Checks company existence, official careers pages, public business footprint,
and whether the specific posting can be found on the company's own site.

This module is currently a **stub** that returns a neutral score.
Real implementation will use web scraping (requests, BeautifulSoup) and
public directory APIs.
"""

from __future__ import annotations

from app.models.schemas import CategoryResult, RiskCategory


async def analyze(
    company_name: str | None = None,
    url: str | None = None,
    consent: bool = False,
    **kwargs,
) -> CategoryResult:
    """Verify company legitimacy via public sources.

    External lookups are only performed when ``consent`` is ``True``.

    Args:
        company_name: Name of the company to verify.
        url: URL of the job listing.
        consent: Whether the user consented to external lookups.

    Returns:
        A :class:`CategoryResult` with score, risk factors, and
        ``analyzed=False`` while this is a stub.
    """
    # TODO: Implement company verification
    #  - Official website / careers page check
    #  - Public business directory lookup
    #  - Posting presence on official site
    #  - Requires consent=True for external calls
    return CategoryResult(score=0.0, risk_factors=[], analyzed=False)
