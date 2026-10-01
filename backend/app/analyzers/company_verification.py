"""Company Verification — category weight 20 %.

Validates company identity against a curated registry of verified employers,
checks domain consistency, and verifies official recruitment footprint.
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
from app.services import web_retrieval

logger = logging.getLogger(__name__)

# Curated registry of recognized employers and their primary domains
VERIFIED_COMPANIES: dict[str, dict] = {
    "tcs": {
        "name": "Tata Consultancy Services (TCS)",
        "domains": ["tcs.com", "tcscareers.com", "tcsionhub.in"],
        "is_major": True,
    },
    "infosys": {
        "name": "Infosys Limited",
        "domains": ["infosys.com"],
        "is_major": True,
    },
    "wipro": {
        "name": "Wipro Limited",
        "domains": ["wipro.com"],
        "is_major": True,
    },
    "cognizant": {
        "name": "Cognizant Technology Solutions",
        "domains": ["cognizant.com"],
        "is_major": True,
    },
    "hcl": {
        "name": "HCL Technologies",
        "domains": ["hcltech.com", "hcl.com"],
        "is_major": True,
    },
    "tech mahindra": {
        "name": "Tech Mahindra",
        "domains": ["techmahindra.com"],
        "is_major": True,
    },
    "amazon": {
        "name": "Amazon",
        "domains": ["amazon.jobs", "amazon.com", "amazon.in"],
        "is_major": True,
    },
    "google": {
        "name": "Google",
        "domains": ["google.com"],
        "is_major": True,
    },
    "microsoft": {
        "name": "Microsoft",
        "domains": ["microsoft.com"],
        "is_major": True,
    },
    "flipkart": {
        "name": "Flipkart",
        "domains": ["flipkartcareers.com", "flipkart.com"],
        "is_major": True,
    },
    "reliance": {
        "name": "Reliance Industries / Jio",
        "domains": ["ril.com", "jio.com"],
        "is_major": True,
    },
    "razorpay": {
        "name": "Razorpay",
        "domains": ["razorpay.com"],
        "is_major": True,
    },
    "swiggy": {
        "name": "Swiggy (Bundl Technologies)",
        "domains": ["swiggy.com"],
        "is_major": True,
    },
    "zomato": {
        "name": "Zomato",
        "domains": ["zomato.com"],
        "is_major": True,
    },
    "stripe": {
        "name": "Stripe Inc.",
        "domains": ["stripe.com"],
        "is_major": True,
    },
    "accenture": {
        "name": "Accenture",
        "domains": ["accenture.com"],
        "is_major": True,
    },
    "capgemini": {
        "name": "Capgemini",
        "domains": ["capgemini.com"],
        "is_major": True,
    },
    "ibm": {
        "name": "IBM",
        "domains": ["ibm.com"],
        "is_major": True,
    },
    "oracle": {
        "name": "Oracle Corporation",
        "domains": ["oracle.com"],
        "is_major": True,
    },
    "deloitte": {
        "name": "Deloitte",
        "domains": ["deloitte.com"],
        "is_major": True,
    },
    "pwc": {
        "name": "PricewaterhouseCoopers (PwC)",
        "domains": ["pwc.com", "pwc.in"],
        "is_major": True,
    },
    "ey": {
        "name": "Ernst & Young (EY)",
        "domains": ["ey.com"],
        "is_major": True,
    },
    "kpmg": {
        "name": "KPMG",
        "domains": ["kpmg.com"],
        "is_major": True,
    },
    "zoho": {
        "name": "Zoho Corporation",
        "domains": ["zoho.com"],
        "is_major": True,
    },
    "apple": {
        "name": "Apple",
        "domains": ["apple.com", "jobs.apple.com"],
        "is_major": True,
    },
    "meta": {
        "name": "Meta Platforms",
        "domains": ["meta.com", "metacareers.com"],
        "is_major": True,
    },
}


TRUSTED_BOARDS = {
    "linkedin.com", "naukri.com", "internshala.com", "unstop.com",
    "indeed.com", "foundit.in", "glassdoor.com", "hirist.com",
}


async def analyze(
    company_name: str | None = None,
    url: str | None = None,
    consent: bool = False,
    page_extraction: "web_retrieval.PageExtraction | None" = None,
    page_attempted: bool = False,
    **kwargs,
) -> CategoryResult:
    """Verify company authenticity and cross-check against careers footprint.

    Args:
        company_name: Claimed employer name.
        url: Listing URL supplied by the user.
        consent: Whether the user consented to external lookups. Live HTTP
            verification of the listing page only runs when this is ``True``.
        page_extraction: Page already retrieved by the pipeline, reused to avoid
            a duplicate fetch.
        page_attempted: ``True`` when the pipeline already attempted retrieval,
            so a ``None`` ``page_extraction`` means the fetch failed rather than
            was skipped.

    Returns:
        A :class:`CategoryResult` with score (0–100), risk factors, and analyzed=True/False.
    """
    has_cmp = bool(company_name and company_name.strip())
    has_url = bool(url and url.strip())

    if not (has_cmp or has_url):
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    risk_factors: list[RiskFactor] = []
    base_score = 0.0

    cmp_norm = (company_name or "").strip().lower()
    matched_entry = None
    if cmp_norm:
        for key, data in VERIFIED_COMPANIES.items():
            name_clean = data["name"].lower()
            if key in cmp_norm or cmp_norm in name_clean or (len(cmp_norm) >= 3 and cmp_norm in name_clean):
                matched_entry = data
                break

    url_domain = ""
    if has_url:
        cleaned_url = url.strip()
        if not cleaned_url.startswith(("http://", "https://")):
            cleaned_url = f"https://{cleaned_url}"
        try:
            url_domain = (urlparse(cleaned_url).hostname or "").lower()
        except Exception:
            pass

    # 1. Company is a recognized enterprise
    if matched_entry:
        official_domains = matched_entry["domains"]
        full_name = matched_entry["name"]

        if url_domain:
            matches_official = any(url_domain == od or url_domain.endswith(f".{od}") for od in official_domains)
            matches_board = any(url_domain == tb or url_domain.endswith(f".{tb}") for tb in TRUSTED_BOARDS)

            if matches_official:
                base_score = 5.0
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.COMPANY_VERIFICATION,
                        severity=Severity.LOW,
                        description=f"Verified official corporate portal for {full_name}.",
                        evidence=f"Listing URL hostname '{url_domain}' matches authentic corporate domain.",
                        source="verified_enterprise_registry",
                        confidence=0.98,
                    )
                )
            elif matches_board:
                base_score = 15.0
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.COMPANY_VERIFICATION,
                        severity=Severity.LOW,
                        description=f"Recognized company ({full_name}) listed on verified job board.",
                        evidence=f"Posting is published on reputable aggregator '{url_domain}'.",
                        source="verified_enterprise_registry",
                        confidence=0.90,
                    )
                )
            else:
                base_score += 65.0
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.COMPANY_VERIFICATION,
                        severity=Severity.HIGH,
                        description=f"Company identity mismatch for {full_name}.",
                        evidence=(
                            f"Listing claims to represent '{full_name}', but URL '{url_domain}' "
                            f"is neither an official domain ({', '.join(official_domains)}) nor a verified job board."
                        ),
                        source="company_domain_discrepancy_scanner",
                        confidence=0.94,
                    )
                )
        else:
            # Company is recognized, no URL provided to contest it
            base_score = 20.0
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.COMPANY_VERIFICATION,
                    severity=Severity.LOW,
                    description=f"Company '{full_name}' is a recognized registered enterprise.",
                    evidence="Matched against enterprise corporate directory. (Submit careers URL for full validation).",
                    source="verified_enterprise_registry",
                    confidence=0.80,
                )
            )
    else:
        # Unrecognized company
        if has_cmp:
            base_score = 35.0
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.COMPANY_VERIFICATION,
                    severity=Severity.MEDIUM,
                    description=f"Company '{company_name}' could not be matched against verified enterprise registry.",
                    evidence="No verified digital corporate footprint found in primary directory. Proceed with standard due diligence.",
                    source="public_business_registry",
                    confidence=0.60,
                )
            )

    # 2. Live listing-page verification via HTTP retrieval (consent-gated).
    #
    # Uses the ``requests`` + ``BeautifulSoup`` retrieval service to fetch the
    # public careers / listing page and confirm the claimed posting actually
    # exists, and to detect payment prompts that indicate a scam page.
    if consent and has_url and url_domain and web_retrieval.is_enabled():
        is_trusted_board = any(
            url_domain == tb or url_domain.endswith(f".{tb}") for tb in TRUSTED_BOARDS
        )
        if not is_trusted_board:
            if page_attempted:
                page = page_extraction  # already fetched by the pipeline
            else:
                page = await web_retrieval.fetch_page(url)
            if page is None:
                base_score += 10.0
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.COMPANY_VERIFICATION,
                        severity=Severity.MEDIUM,
                        description="Live listing page could not be retrieved for verification.",
                        evidence=(
                            f"The listing URL '{url_domain}' did not return a retrievable "
                            "job page (unreachable, non-HTML, or blocked). Unable to "
                            "independently confirm the posting exists."
                        ),
                        source="live_careers_page_verifier",
                        confidence=0.50,
                    )
                )
            elif page.payment_terms:
                base_score += 60.0
                terms = ", ".join(page.payment_terms[:4])
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.COMPANY_VERIFICATION,
                        severity=Severity.HIGH,
                        description="Retrieved listing page solicits direct payment from applicants.",
                        evidence=(
                            f"Live page content at '{page.final_url or url_domain}' contains "
                            f"payment solicitation terms: {terms}. Legitimate employers never "
                            "collect fees on the application page."
                        ),
                        source="live_careers_page_verifier",
                        confidence=0.93,
                    )
                )
            elif page.has_job_posting:
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.COMPANY_VERIFICATION,
                        severity=Severity.LOW,
                        description="Live listing page retrieved and job posting confirmed.",
                        evidence=(
                            f"Retrieved '{page.final_url or url_domain}' (HTTP {page.status_code}); "
                            f"page contains recognisable job-posting content"
                            + (" and a structured JobPosting record" if page.json_ld_job_posting else "")
                            + "."
                        ),
                        source="live_careers_page_verifier",
                        confidence=0.85,
                    )
                )
            else:
                base_score += 25.0
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.COMPANY_VERIFICATION,
                        severity=Severity.MEDIUM,
                        description="Retrieved page contains no verifiable job-posting content.",
                        evidence=(
                            f"'{page.final_url or url_domain}' was reachable (HTTP {page.status_code}) "
                            "but showed no recognisable job description, requirements, or apply form."
                        ),
                        source="live_careers_page_verifier",
                        confidence=0.70,
                    )
                )

    final_score = round(min(max(base_score, 0.0), 100.0), 2)
    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)
