"""Recruiter Verification — category weight 15 %.

Validates recruiter identity by checking email-domain match, public
professional profiles, and contact consistency.

This module is currently a **stub** that returns a neutral score.
"""

from __future__ import annotations

from app.models.schemas import CategoryResult, RiskCategory


async def analyze(
    recruiter_email: str | None = None,
    recruiter_name: str | None = None,
    company_name: str | None = None,
    consent: bool = False,
    **kwargs,
) -> CategoryResult:
    """Verify recruiter identity and contact details.

    External lookups are only performed when ``consent`` is ``True``.

    Args:
        recruiter_email: Recruiter's email address.
        recruiter_name: Recruiter's full name.
        company_name: Company the recruiter claims to represent.
        consent: Whether the user consented to external lookups.

    Returns:
        A :class:`CategoryResult` — stub returns neutral score.
    """
    # TODO: Implement recruiter verification
    #  - Email domain vs. company domain match
    #  - Public professional profile lookup
    #  - Contact pattern consistency
    return CategoryResult(score=0.0, risk_factors=[], analyzed=False)
