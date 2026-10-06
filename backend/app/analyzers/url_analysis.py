"""URL / Website Analysis — category weight 15 %.

Inspects HTTPS status, domain characteristics, URL shorteners, free web hosting,
suspicious top-level domains, and brand impersonation / typosquatting.
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

from datetime import datetime, timezone
import httpx

# Known trusted job boards, aggregators, and enterprise ATS platforms
TRUSTED_JOB_PORTALS = {
    # Job boards & Aggregators
    "linkedin.com", "naukri.com", "internshala.com", "unstop.com",
    "indeed.com", "foundit.in", "monsterindia.com", "glassdoor.com",
    "hirist.com", "instahyre.com", "wellfound.com", "angel.co",
    "ziprecruiter.com", "simplyhired.com",
    # Enterprise ATS (Applicant Tracking Systems)
    "greenhouse.io", "boards.greenhouse.io",
    "lever.co", "jobs.lever.co",
    "myworkdayjobs.com", "workday.com",
    "smartrecruiters.com", "jobs.smartrecruiters.com",
    "ashbyhq.com", "jobs.ashbyhq.com",
    "bamboohr.com", "jobvite.com", "icims.com",
    "recruitee.com", "workable.com", "taleo.net", "brassring.com",
}

# Suspicious or low-reputation TLDs frequently used in phishing/recruitment scams
SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".tk", ".ml", ".ga", ".cf", ".gq", ".work", ".click",
    ".site", ".vip", ".monster", ".fit", ".rest", ".buzz", ".cam", ".live",
    ".shop", ".online", ".info", ".bid", ".club", ".space", ".surf",
}

# Free website builders / form portals masquerading as corporate career portals
FREE_HOSTING_DOMAINS = {
    "wixsite.com", "weebly.com", "blogspot.com", "wordpress.com",
    "sites.google.com", "carrd.co", "notion.site", "render.com",
}

# URL shorteners that obscure real destinations
URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "rb.gy", "shorturl.at", "ow.ly",
}

# Verified official corporate domains (including major global & Indian enterprises)
OFFICIAL_MNC_DOMAINS = {
    "tcs": ["tcs.com", "tcscareers.com", "nextstep.tcs.com", "learning.tcsionhub.in"],
    "infosys": ["infosys.com", "career.infosys.com"],
    "wipro": ["wipro.com", "careers.wipro.com"],
    "cognizant": ["cognizant.com", "careers.cognizant.com"],
    "hcl": ["hcltech.com", "hcl.com"],
    "tech mahindra": ["techmahindra.com", "careers.techmahindra.com"],
    "accenture": ["accenture.com"],
    "capgemini": ["capgemini.com"],
    "ibm": ["ibm.com"],
    "oracle": ["oracle.com"],
    "deloitte": ["deloitte.com"],
    "pwc": ["pwc.com", "pwc.in"],
    "ey": ["ey.com"],
    "kpmg": ["kpmg.com"],
    "amazon": ["amazon.jobs", "amazon.com", "amazon.in"],
    "google": ["google.com", "careers.google.com"],
    "microsoft": ["microsoft.com", "careers.microsoft.com"],
    "meta": ["meta.com", "metacareers.com"],
    "apple": ["apple.com", "jobs.apple.com"],
    "zoho": ["zoho.com"],
    "flipkart": ["flipkartcareers.com", "flipkart.com"],
    "reliance": ["ril.com", "jio.com"],
    "netflix": ["netflix.com", "jobs.netflix.com"],
    "salesforce": ["salesforce.com", "careers.salesforce.com"],
    "uber": ["uber.com", "careers.uber.com"],
    "swiggy": ["swiggy.com", "careers.swiggy.com"],
    "zomato": ["zomato.com", "careers.zomato.com"],
    "paytm": ["paytm.com", "careers.paytm.com"],
    "adobe": ["adobe.com", "careers.adobe.com"],
    "cisco": ["cisco.com", "jobs.cisco.com"],
    "intel": ["intel.com", "jobs.intel.com"],
    "nvidia": ["nvidia.com"],
    "stripe": ["stripe.com"],
    "razorpay": ["razorpay.com"],
}


async def _check_domain_dns_resolution(domain: str) -> bool:
    """Verify live DNS host resolution (A records) via Cloudflare/Google DoH."""
    url_cf = f"https://cloudflare-dns.com/dns-query?name={domain}&type=A"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url_cf, headers={"accept": "application/dns-json"})
            if resp.status_code == 200:
                answers = resp.json().get("Answer", [])
                if answers:
                    return True
    except Exception as exc:
        logger.debug("DNS A resolution check failed via Cloudflare for %s: %s", domain, exc)

    # Google DoH fallback
    url_gg = f"https://dns.google/resolve?name={domain}&type=A"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url_gg)
            if resp.status_code == 200:
                answers = resp.json().get("Answer", [])
                if answers:
                    return True
    except Exception as exc:
        logger.debug("DNS A resolution check failed via Google for %s: %s", domain, exc)

    return False


async def _check_domain_rdap(domain: str) -> dict | None:
    """Query RDAP registry to determine domain creation date and registration age."""
    # Strip subdomains for common multi-level domains
    parts = domain.split(".")
    if len(parts) > 2 and parts[-2] not in {"co", "com", "org", "net", "gov", "edu", "ac"}:
        root_domain = ".".join(parts[-2:])
    elif len(parts) > 3:
        root_domain = ".".join(parts[-3:])
    else:
        root_domain = domain

    url = f"https://rdap.org/domain/{root_domain}"
    try:
        async with httpx.AsyncClient(timeout=2.5, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Accept": "application/rdap+json, application/json"})
            if resp.status_code == 200:
                data = resp.json()
                for event in data.get("events", []):
                    action = event.get("eventAction", "").lower()
                    if action in {"registration", "created"}:
                        date_str = event.get("eventDate", "")
                        if date_str:
                            clean_date = date_str.replace("Z", "+00:00")
                            created_dt = datetime.fromisoformat(clean_date)
                            now = datetime.now(timezone.utc)
                            age_days = (now - created_dt).days
                            return {
                                "root_domain": root_domain,
                                "created_date": created_dt.strftime("%Y-%m-%d"),
                                "age_days": max(0, age_days),
                            }
    except Exception as exc:
        logger.debug("RDAP lookup skipped or failed for %s: %s", domain, exc)
    return None



async def analyze(
    url: str | None = None,
    company_name: str | None = None,
    consent: bool = False,
    **kwargs,
) -> CategoryResult:
    """Analyse submitted URL for security, domain legitimacy, and impersonation.

    Returns:
        A :class:`CategoryResult` with score (0–100), risk factors, and analyzed=True/False.
    """
    if not url or not url.strip():
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    cleaned_url = url.strip()
    if not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = f"https://{cleaned_url}"

    try:
        parsed = urlparse(cleaned_url)
    except Exception as exc:
        logger.error("Error parsing URL %s: %s", url, exc)
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    domain = (parsed.hostname or "").lower()
    scheme = (parsed.scheme or "").lower()

    if not domain:
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    risk_factors: list[RiskFactor] = []
    base_score = 0.0

    # 1. Scheme check: Insecure HTTP
    if scheme == "http":
        base_score += 35.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.HIGH,
                description="Unencrypted HTTP protocol detected instead of secure HTTPS.",
                evidence=f"The job listing URL '{cleaned_url}' transmits data over insecure plaintext HTTP.",
                source="url_protocol_checker",
                confidence=0.95,
            )
        )

    # 2. URL Shortener check
    if any(domain == shortener or domain.endswith(f".{shortener}") for shortener in URL_SHORTENERS):
        base_score += 45.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.HIGH,
                description="URL shortener obfuscates the destination website.",
                evidence=f"Domain '{domain}' is a redirection service, commonly used to hide fraudulent portals.",
                source="url_shortener_checker",
                confidence=0.90,
            )
        )

    # 3. Free Web Hosting / Form Portal check
    if any(host in domain for host in FREE_HOSTING_DOMAINS) or "forms.gle" in domain or "docs.google.com" in domain:
        base_score += 55.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.HIGH,
                description="Hiring application hosted on free website builder or generic Google Form.",
                evidence=f"Domain '{domain}' indicates the posting is hosted on a free or informal host rather than an enterprise domain.",
                source="free_host_detector",
                confidence=0.88,
            )
        )

    # 4. Suspicious TLD check
    if any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS):
        base_score += 40.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.HIGH,
                description="High-risk top-level domain frequently associated with disposable scam sites.",
                evidence=f"Domain '{domain}' uses a low-cost or disposable TLD.",
                source="tld_reputation_checker",
                confidence=0.85,
            )
        )

    # 5. Brand Impersonation / Typosquatting against Top MNCs
    # e.g., tcs-jobs.net, infosys-careers-portal.org, etc.
    impersonated = False
    for brand, legit_domains in OFFICIAL_MNC_DOMAINS.items():
        # Check if brand name is in domain but NOT an official domain
        if brand in domain and not any(domain == ld or domain.endswith(f".{ld}") for ld in legit_domains):
            # Check if it's a known trusted aggregator (like linkedin.com/jobs/...)
            is_trusted_board = any(domain == tj or domain.endswith(f".{tj}") for tj in TRUSTED_JOB_PORTALS)
            if not is_trusted_board:
                impersonated = True
                base_score += 60.0
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.URL_WEBSITE,
                        severity=Severity.HIGH,
                        description=f"Potential brand impersonation detected for '{brand.upper()}'.",
                        evidence=f"Domain '{domain}' contains '{brand}', but does not match official career domains ({', '.join(legit_domains)}).",
                        source="domain_impersonation_detector",
                        confidence=0.92,
                    )
                )
                break

    # 6. Check company name mismatch if company_name was provided
    if company_name and company_name.strip() and not impersonated:
        cmp_clean = re.sub(r"[^a-z0-9]", "", company_name.lower())
        is_trusted_board = any(domain == tj or domain.endswith(f".{tj}") for tj in TRUSTED_JOB_PORTALS)
        
        # If not a trusted job board and company name is completely absent in domain
        if not is_trusted_board and len(cmp_clean) > 3:
            parts = domain.split(".")
            domain_core = parts[-2] if len(parts) >= 2 else parts[0]
            if cmp_clean not in domain_core and domain_core not in cmp_clean:
                # Add moderate mismatch notice
                base_score += 15.0
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.URL_WEBSITE,
                        severity=Severity.LOW,
                        description="Domain name differs from stated company name.",
                        evidence=f"Stated company '{company_name}' does not match host '{domain}'. (May be an external agency or job aggregator).",
                        source="company_domain_matcher",
                        confidence=0.65,
                    )
                )

    # 7. Check if domain is a verified trusted job board
    is_trusted = any(domain == tj or domain.endswith(f".{tj}") for tj in TRUSTED_JOB_PORTALS)
    if is_trusted and not any(rf.severity == Severity.HIGH for rf in risk_factors):
        base_score = 5.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.LOW,
                description="Verified professional job board or recruitment platform.",
                evidence=f"Hosted on reputable aggregator '{domain}'.",
                source="trusted_portal_registry",
                confidence=0.90,
            )
        )

    # 8. Live RDAP Domain Age & Registration Verification (when external lookups permitted)
    # 8. Live RDAP & DNS Host Verification (when external lookups permitted)
    if consent and not is_trusted:
        # Check if domain resolves to active host records
        is_resolvable = await _check_domain_dns_resolution(domain)
        if not is_resolvable:
            base_score += 65.0
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.URL_WEBSITE,
                    severity=Severity.HIGH,
                    description="Unresolvable or non-existent domain name.",
                    evidence=(
                        f"Domain '{domain}' does not have any active DNS A host records in global nameservers. "
                        "The site cannot be resolved and is likely fraudulent or already deactivated."
                    ),
                    source="dns_host_verifier",
                    confidence=0.96,
                )
            )

        rdap_info = await _check_domain_rdap(domain)
        if rdap_info:
            age_days = rdap_info["age_days"]
            created_date = rdap_info["created_date"]
            root_domain = rdap_info["root_domain"]

            if age_days <= 60:
                base_score += 45.0
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.URL_WEBSITE,
                        severity=Severity.HIGH,
                        description="Newly registered domain (< 60 days old) detected.",
                        evidence=(
                            f"Domain '{root_domain}' was created very recently on {created_date} "
                            f"({age_days} days ago). Disposable and recently purchased domains "
                            f"are heavily leveraged in fraudulent recruitment campaigns."
                        ),
                        source="rdap_domain_age_verifier",
                        confidence=0.92,
                    )
                )
            elif age_days >= 365 and not any(rf.severity == Severity.HIGH for rf in risk_factors):
                years_active = round(age_days / 365.25, 1)
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.URL_WEBSITE,
                        severity=Severity.LOW,
                        description="Domain possesses established registration longevity.",
                        evidence=(
                            f"Domain '{root_domain}' has been registered since {created_date} "
                            f"(~{years_active} years active)."
                        ),
                        source="rdap_domain_age_verifier",
                        confidence=0.85,
                    )
                )

    final_score = round(min(max(base_score, 0.0), 100.0), 2)
    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)

