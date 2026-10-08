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

# Known trusted job boards and platforms
TRUSTED_JOB_PORTALS = {
    "linkedin.com", "naukri.com", "internshala.com", "unstop.com",
    "indeed.com", "foundit.in", "monsterindia.com", "glassdoor.com",
    "hirist.com", "instahyre.com", "wellfound.com", "angel.co",
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

# Special-purpose / documentation / reserved domains (RFC 2606 / RFC 6761)
RESERVED_DOC_DOMAINS = {
    "example.com", "example.org", "example.net", "example.edu",
    "test.com", "invalid.com", "localhost",
}

# Dedicated payment gateway hosts and checkout subdomains
PAYMENT_GATEWAY_HOSTS = {
    "pages.razorpay.com", "razorpay.me", "rzp.io",
    "buy.stripe.com", "checkout.stripe.com", "pay.stripe.com",
    "pay.instamojo.com", "instamojo.com", "imojo.in",
    "paypal.me", "cashfree.com", "payments.cashfree.com",
    "payu.in", "payumoney.com", "p-y.tm", "paytm.me",
}

PAYMENT_URL_PATTERNS = [
    r"/pl_[a-zA-Z0-9]+",
    r"/(payment|checkout|invoice|order|billing|pay-now|payment-page|payment-link)(/|\?|$)",
    r"/(buy|pay)/[a-zA-Z0-9_-]+",
]

PAYMENT_PROVIDER_ROOTS = {
    "razorpay.com", "stripe.com", "paypal.com", "instamojo.com", "cashfree.com", "payu.in", "paytm.com",
}


def _is_host_or_subdomain(domain: str, candidates: set[str]) -> bool:
    """Return True if domain exactly matches or is a subdomain of any candidate."""
    return any(domain == c or domain.endswith(f".{c}") for c in candidates)


def is_payment_gateway_url(cleaned_url: str) -> tuple[bool, str]:
    """Check if URL points to a payment gateway, checkout link, or payment page."""
    if not cleaned_url:
        return False, ""
    try:
        parsed = urlparse(cleaned_url)
        domain = (parsed.hostname or "").lower()
        path_query = f"{parsed.path}?{parsed.query}".lower()
    except Exception:
        return False, ""

    for host in PAYMENT_GATEWAY_HOSTS:
        if domain == host or domain.endswith(f".{host}"):
            return True, f"Payment gateway domain '{domain}'"

    is_provider = any(domain == p or domain.endswith(f".{p}") for p in PAYMENT_PROVIDER_ROOTS)
    for pattern in PAYMENT_URL_PATTERNS:
        if re.search(pattern, path_query):
            if is_provider:
                return True, f"Payment page link pattern on payment domain '{domain}'"
            return True, "Payment/checkout URL pattern detected"

    return False, ""


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
}


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
    page_extraction: Any | None = None,
    page_attempted: bool = False,
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

    # 0. Dedicated Payment Gateway / Checkout Link check
    is_payment, payment_reason = is_payment_gateway_url(cleaned_url)
    if is_payment:
        base_score += 75.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.HIGH,
                description="Payment gateway or checkout page URL submitted as a job posting.",
                evidence=(
                    f"Listing URL '{cleaned_url}' points to a payment processing endpoint or transaction link "
                    f"({payment_reason}), not an authentic corporate job portal or career board."
                ),
                source="payment_gateway_url_detector",
                confidence=0.98,
            )
        )

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

    # 2. URL Shortener check (exact or subdomain match — avoids substring false positives like microsoft.com containing 't.co')
    if _is_host_or_subdomain(domain, URL_SHORTENERS):
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
    if _is_host_or_subdomain(domain, FREE_HOSTING_DOMAINS) or domain in ("forms.gle", "docs.google.com") or domain.endswith((".forms.gle", ".docs.google.com")):
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

    # 4. Reserved / Documentation Domain check (RFC 2606 / RFC 6761)
    is_reserved_doc_domain = (
        domain in RESERVED_DOC_DOMAINS
        or any(domain.endswith(f".{r}") for r in RESERVED_DOC_DOMAINS)
        or domain.endswith((".example", ".test", ".invalid", ".localhost"))
    )
    if is_reserved_doc_domain:
        base_score += 65.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.HIGH,
                description="Reserved documentation/placeholder domain (RFC 2606) detected.",
                evidence=(
                    f"Domain '{domain}' is an IANA-reserved special-use domain designated for "
                    "documentation and testing examples. It cannot host genuine employment opportunities."
                ),
                source="reserved_domain_detector",
                confidence=0.99,
            )
        )

    # 5. Suspicious TLD check
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

    # 6. Brand Impersonation / Typosquatting against Top MNCs
    impersonated = False
    for brand, legit_domains in OFFICIAL_MNC_DOMAINS.items():
        if brand in domain and not any(domain == ld or domain.endswith(f".{ld}") for ld in legit_domains):
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

    # 7. Suspicious Scam Keywords in URL Path & Query
    path_query_str = f"{parsed.path} {parsed.query}".lower()
    normalized_pq = re.sub(r"[/_?&=+.-]+", " ", path_query_str)
    pq_tokens = set(normalized_pq.split())

    high_risk_phrases = [
        "registration fee", "training fee", "processing fee", "security deposit",
        "refundable deposit", "application fee", "joining fee", "pay now",
        "telegram task", "whatsapp task", "wire transfer", "crypto payment",
    ]
    matched_scam_phrases = [p for p in high_risk_phrases if p in normalized_pq]

    has_fee_term = bool(pq_tokens & {"fee", "fees", "payment", "pay", "deposit", "charge", "cost"})
    has_selection_term = bool(pq_tokens & {"selected", "selection", "shortlisted"})
    has_training_term = bool(pq_tokens & {"training", "internship", "stipend"})

    combo_matches = []
    if has_selection_term and has_fee_term:
        combo_matches.append("selection + fee")
    if has_training_term and has_fee_term and not matched_scam_phrases:
        combo_matches.append("training/internship + fee")
    if has_selection_term and has_training_term and has_fee_term:
        combo_matches.append("selected + internship + fee")

    scam_url_signals = matched_scam_phrases + combo_matches
    if scam_url_signals:
        base_score += 65.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.HIGH,
                description="Deceptive scam keywords detected in URL path (fee/payment/selection trope).",
                evidence=(
                    f"URL contains high-risk recruitment fraud indicators: {', '.join(scam_url_signals)}. "
                    "Legitimate corporate employers never charge applicant fees or condition job selection on payments."
                ),
                source="url_scam_keyword_detector",
                confidence=0.96,
            )
        )
    elif pq_tokens & {"registration", "fee", "payment", "selected", "deposit"}:
        found_tokens = sorted(pq_tokens & {"registration", "fee", "payment", "selected", "deposit"})
        base_score += 35.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.MEDIUM,
                description="Suspicious recruitment terminology found in URL path.",
                evidence=f"URL contains sensitive hiring terms ({', '.join(found_tokens)}). Verify whether fees or deposits are being solicited.",
                source="url_scam_keyword_detector",
                confidence=0.75,
            )
        )

    # 8. Live HTTP Reachability / Status Code Check (when page was retrieved)
    if page_extraction is not None:
        status = getattr(page_extraction, "status_code", 0)
        if status in (404, 410):
            base_score += 60.0
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.URL_WEBSITE,
                    severity=Severity.HIGH,
                    description="Listing URL returned HTTP 404 (Not Found); destination is broken or non-existent.",
                    evidence=(
                        f"The listing URL returned HTTP {status} Client Error. The job posting does not exist, "
                        "has been taken down, or points to an invalid address. Non-existent opportunities cannot be verified."
                    ),
                    source="url_reachability_checker",
                    confidence=0.95,
                )
            )
        elif status >= 400:
            # Verification failure (anti-bot 403, rate limit 429, or server error 50x) — NOT fraud evidence
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.URL_WEBSITE,
                    severity=Severity.LOW,
                    description=f"Destination server restricted automated inspection (HTTP {status}).",
                    evidence=f"Listing URL at '{domain}' returned HTTP status {status} (anti-bot header or server restriction). Inspection relied on domain authentication.",
                    source="url_reachability_checker",
                    confidence=0.40,
                )
            )
    elif page_attempted:
        # Verification failure (connection timeout, DNS lookup error, or unreachable) — NOT fraud evidence
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.URL_WEBSITE,
                severity=Severity.LOW,
                description="Listing URL could not be fetched live (connection timeout or unreachable).",
                evidence="Could not complete live fetch of the listing URL. Verification degraded gracefully to static signals.",
                source="url_reachability_checker",
                confidence=0.40,
            )
        )

    # 9. Check company name mismatch if company_name was provided
    if company_name and company_name.strip() and not impersonated:
        cmp_clean = re.sub(r"[^a-z0-9]", "", company_name.lower())
        is_trusted_board = any(domain == tj or domain.endswith(f".{tj}") for tj in TRUSTED_JOB_PORTALS)
        if not is_trusted_board and len(cmp_clean) > 3:
            parts = domain.split(".")
            domain_core = parts[-2] if len(parts) >= 2 else parts[0]
            if cmp_clean not in domain_core and domain_core not in cmp_clean:
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

    # 10. Check if domain is a verified trusted job board
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

    # 11. Live RDAP Domain Age & Registration Verification (when external lookups permitted)
    if consent and not is_trusted:
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
            elif age_days >= 365:
                # Longevity praise is strictly guarded: an old domain registration must NOT
                # override 404 dead links, scam keywords, reserved documentation domains, or active risk factors.
                has_any_concern = (
                    base_score > 0.0
                    or any(rf.severity in (Severity.HIGH, Severity.MEDIUM) for rf in risk_factors)
                    or is_reserved_doc_domain
                    or (page_extraction is not None and getattr(page_extraction, "status_code", 0) >= 400)
                )
                if not has_any_concern:
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


