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
}

TRUSTED_BOARDS = {
    "linkedin.com", "naukri.com", "internshala.com", "unstop.com",
    "indeed.com", "foundit.in", "glassdoor.com", "hirist.com",
}


async def analyze(
    company_name: str | None = None,
    url: str | None = None,
    consent: bool = False,
    **kwargs,
) -> CategoryResult:
    """Verify company authenticity and cross-check against careers footprint.

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

    final_score = round(min(max(base_score, 0.0), 100.0), 2)
    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)
