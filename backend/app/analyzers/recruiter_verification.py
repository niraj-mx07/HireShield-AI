"""Recruiter Verification — category weight 15 %.

Validates recruiter email domains, communication channels, and identity consistency.
Flags free-webmail recruiters claiming enterprise affiliation and unsolicited chat recruitment.
"""

from __future__ import annotations

import logging
import re

from app.models.schemas import (
    CategoryResult,
    RiskCategory,
    RiskFactor,
    Severity,
)

logger = logging.getLogger(__name__)

import httpx

# Common free webmail providers
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "yahoo.co.in", "outlook.com",
    "hotmail.com", "rediffmail.com", "live.com", "aol.com", "icloud.com",
    "mail.com", "protonmail.com", "zoho.com", "yandex.com",
}

# Major enterprises where recruiters NEVER hire via @gmail/@yahoo
KNOWN_ENTERPRISES = {
    "tcs", "tata consultancy services", "infosys", "wipro", "cognizant",
    "hcl", "tech mahindra", "amazon", "google", "microsoft", "flipkart",
    "reliance", "jio", "deloitte", "accenture", "ibm", "capgemini", "ey",
    "ernst & young", "pwc", "kpmg", "apple", "meta", "oracle",
}


async def _check_domain_mx(domain: str) -> list[str]:
    """Query Cloudflare DNS-over-HTTPS for DNS MX mail exchanger records."""
    url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=MX"
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(url, headers={"accept": "application/dns-json"})
            if resp.status_code == 200:
                data = resp.json()
                answers = data.get("Answer", [])
                return [ans.get("data", "") for ans in answers if ans.get("data")]
    except Exception as exc:
        logger.debug("DNS MX lookup skipped or failed for %s: %s", domain, exc)
    return []



async def analyze(
    recruiter_email: str | None = None,
    recruiter_name: str | None = None,
    recruiter_phone: str | None = None,
    company_name: str | None = None,
    message: str | None = None,
    consent: bool = False,
    **kwargs,
) -> CategoryResult:
    """Analyse recruiter credentials, email domain, and communication channels.

    Returns:
        A :class:`CategoryResult` with score (0–100), risk factors, and analyzed=True/False.
    """
    has_email = bool(recruiter_email and recruiter_email.strip())
    has_name = bool(recruiter_name and recruiter_name.strip())
    has_phone = bool(recruiter_phone and recruiter_phone.strip())
    has_msg = bool(message and message.strip())

    if not (has_email or has_name or has_phone or has_msg):
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    risk_factors: list[RiskFactor] = []
    base_score = 0.0

    email_domain = ""
    if has_email:
        email = recruiter_email.strip().lower()
        if "@" in email:
            email_domain = email.split("@")[-1].strip()

    cmp_norm = (company_name or "").strip().lower()
    is_major_enterprise = any(ent in cmp_norm for ent in KNOWN_ENTERPRISES)

    # 1. Free email domain check
    if email_domain in FREE_EMAIL_DOMAINS:
        if is_major_enterprise:
            base_score += 75.0
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.RECRUITER_VERIFICATION,
                    severity=Severity.HIGH,
                    description=f"Recruiter uses free webmail ({email_domain}) while claiming to represent an enterprise.",
                    evidence=(
                        f"Official recruitment at '{company_name}' is conducted exclusively via corporate email domains, "
                        f"not public addresses ({recruiter_email})."
                    ),
                    source="corporate_email_domain_validator",
                    confidence=0.95,
                )
            )
        else:
            base_score += 40.0
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.RECRUITER_VERIFICATION,
                    severity=Severity.MEDIUM,
                    description="Recruiter uses a personal or free email address.",
                    evidence=f"Email host '{email_domain}' is a generic webmail provider. Legitimate businesses typically use their own domain.",
                    source="free_email_detector",
                    confidence=0.85,
                )
            )
    elif email_domain:
        # Corporate domain — check if domain matches stated company
        if cmp_norm and len(cmp_norm) > 3:
            clean_cmp = re.sub(r"[^a-z0-9]", "", cmp_norm)
            domain_core = email_domain.split(".")[0]
            if clean_cmp in domain_core or domain_core in clean_cmp:
                base_score = max(base_score - 10.0, 5.0)
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.RECRUITER_VERIFICATION,
                        severity=Severity.LOW,
                        description="Recruiter email matches corporate domain.",
                        evidence=f"Email domain '{email_domain}' corresponds with company identity '{company_name}'.",
                        source="corporate_email_verifier",
                        confidence=0.90,
                    )
                )

        # Check live DNS MX records for corporate email domains (when consent granted)
        if consent:
            mx_records = await _check_domain_mx(email_domain)
            if not mx_records:
                base_score += 55.0
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.RECRUITER_VERIFICATION,
                        severity=Severity.HIGH,
                        description="Recruiter email domain has no DNS MX mail exchangers.",
                        evidence=(
                            f"Domain '{email_domain}' has no active DNS MX mail routing records. "
                            "It cannot receive or send authentic enterprise mail and is likely a disposable "
                            "or spoofed domain."
                        ),
                        source="dns_mx_verifier",
                        confidence=0.95,
                    )
                )
            elif not any(rf.severity == Severity.HIGH for rf in risk_factors):
                top_mx = mx_records[0].split()[-1]
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.RECRUITER_VERIFICATION,
                        severity=Severity.LOW,
                        description="Recruiter email domain has operational mail exchangers.",
                        evidence=f"DNS MX record confirmed active mail routing server: '{top_mx}'.",
                        source="dns_mx_verifier",
                        confidence=0.88,
                    )
                )


    # 2. Telegram / WhatsApp channel recruitment check
    combined_content = f"{message or ''} {recruiter_phone or ''} {recruiter_name or ''}".lower()
    telegram_match = re.search(r"(@[a-zA-Z0-9_]{4,}|t\.me/[a-zA-Z0-9_]+|telegram)", combined_content)
    whatsapp_match = re.search(r"(whatsapp|wa\.me/|\+91\s?[6-9]\d{9})", combined_content)

    if telegram_match:
        base_score += 50.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.RECRUITER_VERIFICATION,
                severity=Severity.HIGH,
                description="Interview or hiring communication conducted primarily via Telegram.",
                evidence=f"Telegram contact '{telegram_match.group(0)}' referenced as primary hiring channel. Legitimate firms do not use anonymous Telegram handles.",
                source="unverified_chat_channel_detector",
                confidence=0.92,
            )
        )

    if whatsapp_match and not has_email:
        base_score += 35.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.RECRUITER_VERIFICATION,
                severity=Severity.MEDIUM,
                description="Job offer initiated solely via WhatsApp without verifiable corporate email.",
                evidence="Unsolicited WhatsApp messaging is a standard channel for high-volume recruitment fraud.",
                source="whatsapp_recruitment_detector",
                confidence=0.80,
            )
        )

    final_score = round(min(max(base_score, 0.0), 100.0), 2)
    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)
