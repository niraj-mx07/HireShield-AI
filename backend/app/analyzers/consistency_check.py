"""Information Consistency — category weight 5 %.

Cross-checks data across the listing description, URL, recruiter email,
message content, and document text to detect identity contradictions.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from app.models.schemas import (
    CategoryResult,
    RiskCategory,
    RiskFactor,
    Severity,
)

logger = logging.getLogger(__name__)


async def analyze(
    description: str | None = None,
    url: str | None = None,
    company_name: str | None = None,
    recruiter_email: str | None = None,
    message: str | None = None,
    document_text: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Detect discrepancies and contradictions across submitted sources.

    Returns:
        A :class:`CategoryResult` with score (0–100), risk factors, and analyzed=True/False.
    """
    # Count how many distinct information vectors were provided
    sources_count = sum([
        bool(description and description.strip()),
        bool(url and url.strip()),
        bool(company_name and company_name.strip()),
        bool(recruiter_email and recruiter_email.strip()),
        bool(message and message.strip()),
        bool(document_text and document_text.strip()),
    ])

    # Consistency requires cross-referencing at least two distinct inputs
    if sources_count < 2:
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    risk_factors: list[RiskFactor] = []
    base_score = 0.0

    # 1. Recruiter email domain vs. URL domain mismatch
    if recruiter_email and url:
        try:
            email_domain = recruiter_email.split("@")[-1].strip().lower()
            url_domain = (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower()
            
            # Remove www. or careers. subdomains
            clean_url_dom = re.sub(r"^(?:www|careers|jobs|mail)\.", "", url_domain)
            clean_email_dom = re.sub(r"^(?:www|careers|jobs|mail)\.", "", email_domain)

            # If neither is a free webmail nor a trusted board
            free_mails = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com"}
            boards = {"linkedin.com", "naukri.com", "internshala.com", "indeed.com"}

            if clean_email_dom not in free_mails and clean_url_dom not in boards:
                if clean_url_dom != clean_email_dom and clean_url_dom not in clean_email_dom and clean_email_dom not in clean_url_dom:
                    base_score += 55.0
                    risk_factors.append(
                        RiskFactor(
                            category=RiskCategory.INFORMATION_CONSISTENCY,
                            severity=Severity.HIGH,
                            description="Cross-source domain conflict between job URL and recruiter email.",
                            evidence=f"Listing URL domain '{clean_url_dom}' conflicts with recruiter email domain '{clean_email_dom}'.",
                            source="cross_domain_consistency_checker",
                            confidence=0.92,
                        )
                    )
        except Exception as exc:
            logger.debug("Error checking domain consistency: %s", exc)

    # 2. Recruiter email domain vs stated company name mismatch
    if recruiter_email and company_name:
        try:
            email_domain = recruiter_email.split("@")[-1].strip().lower()
            clean_email_dom = re.sub(r"^(?:www|careers|jobs|mail)\.", "", email_domain)
            free_mails = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com", "free-webmail.com"}
            if clean_email_dom not in free_mails:
                cmp_clean = re.sub(r"[^a-z0-9]", "", company_name.lower())
                domain_core = clean_email_dom.split(".")[0]
                if len(cmp_clean) > 3 and cmp_clean not in domain_core and domain_core not in cmp_clean:
                    base_score += 45.0
                    risk_factors.append(
                        RiskFactor(
                            category=RiskCategory.INFORMATION_CONSISTENCY,
                            severity=Severity.HIGH,
                            description="Recruiter email domain conflicts with stated company name.",
                            evidence=f"Recruiter email domain '{clean_email_dom}' does not match stated company '{company_name}'.",
                            source="employer_email_consistency_checker",
                            confidence=0.90,
                        )
                    )
        except Exception as exc:
            logger.debug("Error checking email/company consistency: %s", exc)

    # 3. Stated company vs document / message company mismatch
    if company_name and (document_text or message):
        cmp_clean = re.sub(r"[^a-z0-9]", "", company_name.lower())
        ref_text = f"{document_text or ''} {message or ''}".lower()
        if len(cmp_clean) > 4 and cmp_clean not in re.sub(r"[^a-z0-9]", "", ref_text):
            # Stated company name is not found anywhere in the offer document or message text
            base_score += 30.0
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.INFORMATION_CONSISTENCY,
                    severity=Severity.MEDIUM,
                    description="Stated employer name absent from submitted document or message.",
                    evidence=f"Specified company '{company_name}' does not appear in the body of the attached communication or offer text.",
                    source="entity_consistency_validator",
                    confidence=0.75,
                )
            )

    # 3. If sources were consistent
    if not risk_factors:
        base_score = 5.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.INFORMATION_CONSISTENCY,
                severity=Severity.LOW,
                description="Cross-channel data points are mutually consistent.",
                evidence="No identity, domain, or employer conflicts detected across submitted sources.",
                source="entity_consistency_validator",
                confidence=0.88,
            )
        )

    final_score = round(min(max(base_score, 0.0), 100.0), 2)
    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)
