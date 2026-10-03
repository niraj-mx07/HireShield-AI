"""Recruiter Verification — category weight 15 %.

Validates recruiter email domains, communication channels, and identity consistency.
Flags free-webmail recruiters claiming enterprise affiliation and unsolicited chat recruitment.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum

import httpx

from app.models.schemas import (
    CRITICAL_INFRA_FAILURE_SOURCE,
    CategoryResult,
    RiskCategory,
    RiskFactor,
    Severity,
)

logger = logging.getLogger(__name__)

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


# Globally recognized enterprise mail domains (Fortune-500 / large caps).
# These provably route mail, so a *failed* lookup against one of them must
# never be reported as "no MX records" — it means our resolver timed out.
VERIFIED_ENTERPRISE_DOMAINS: frozenset[str] = frozenset({
    "tcs.com", "infosys.com", "wipro.com", "cognizant.com", "hcl.com",
    "hcltech.com", "techmahindra.com", "accenture.com", "capgemini.com",
    "deloitte.com", "kpmg.com", "pwc.com", "ey.com", "google.com",
    "microsoft.com", "amazon.com", "apple.com", "meta.com", "ibm.com",
    "oracle.com", "salesforce.com", "adobe.com", "flipkart.com",
    "linkedin.com", "reliancejio.com",
})

# --- DNS MX lookup tuning -------------------------------------------------
# Enterprise DNS is slow and often cached behind flaky resolvers, so a single
# timed-out query must be retried rather than mistaken for a dead domain.
_MX_ATTEMPTS = 3                # strict retry count for one domain
_MX_TIMEOUT_SECONDS = 2.5       # per-attempt timeout
_MX_BACKOFF_SECONDS = 0.25      # linear backoff between attempts

# --- Recruiter Verification score behaviour -------------------------------
_MX_FAILURE_BONUS = 55.0
_MX_FAILURE_SCORE_FLOOR = 65.0  # a failed MX check lands in the FAIL band
_MX_INDETERMINATE_PENALTY = 10.0


class MxLookupStatus(str, Enum):
    """Outcome of an MX lookup.

    ``NO_RECORDS`` means the resolver *authoritatively* answered that no mail
    exchanger exists.  ``INDETERMINATE`` means we could not find out.  The two
    must never be conflated: only the former proves a mail-infrastructure
    failure, the latter only justifies a re-scan.
    """

    FOUND = "found"
    NO_RECORDS = "no_records"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class MxLookupResult:
    """Structured MX lookup outcome."""

    status: MxLookupStatus
    records: tuple[str, ...] = ()
    attempts: int = 0
    detail: str = ""


def is_verified_enterprise_domain(domain: str) -> bool:
    """True when *domain* belongs to a globally recognized enterprise."""
    normalized = (domain or "").strip().lower().rstrip(".")
    if not normalized:
        return False
    return any(
        normalized == apex or normalized.endswith(f".{apex}")
        for apex in VERIFIED_ENTERPRISE_DOMAINS
    )


async def _fetch_dns_json(domain: str) -> dict:
    """Perform a single DNS-over-HTTPS MX query.

    Raises on any transport or HTTP-level failure so the retry loop can tell a
    network problem apart from an authoritative "no records" answer.
    """
    url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=MX"
    async with httpx.AsyncClient(timeout=_MX_TIMEOUT_SECONDS) as client:
        resp = await client.get(url, headers={"accept": "application/dns-json"})
        resp.raise_for_status()
        return resp.json()


async def _check_domain_mx(domain: str) -> MxLookupResult:
    """Resolve MX records with a strict retry mechanism.

    Timeouts, connect errors, HTTP failures and SERVFAIL/REFUSED answers are
    retried, then reported as :class:`MxLookupStatus.INDETERMINATE` — never as
    ``NO_RECORDS``.  Only an authoritative answer with zero MX records is
    reported as ``NO_RECORDS``.
    """
    if not (domain or "").strip():
        return MxLookupResult(MxLookupStatus.INDETERMINATE, detail="no domain supplied")

    last_detail = ""
    for attempt in range(1, _MX_ATTEMPTS + 1):
        try:
            data = await _fetch_dns_json(domain)
        except Exception as exc:  # noqa: BLE001 - any transport/HTTP failure
            last_detail = f"{type(exc).__name__}: {exc}"
            logger.debug(
                "DNS MX attempt %d/%d failed for %s: %s", attempt, _MX_ATTEMPTS, domain, exc
            )
            if attempt < _MX_ATTEMPTS:
                await asyncio.sleep(_MX_BACKOFF_SECONDS * attempt)
            continue

        status_code = data.get("Status", 0)
        if status_code in (2, 5):  # SERVFAIL / REFUSED -> resolver trouble
            last_detail = f"resolver returned rcode {status_code}"
            if attempt < _MX_ATTEMPTS:
                await asyncio.sleep(_MX_BACKOFF_SECONDS * attempt)
            continue

        # Only type 15 answers count as mail exchangers; a CNAME (type 5) or
        # other record returned alongside the answer is not an MX record.
        answers = data.get("Answer") or []
        mx_records = tuple(
            str(ans.get("data", "")).strip()
            for ans in answers
            if ans.get("type") == 15 and ans.get("data")
        )
        if mx_records:
            return MxLookupResult(MxLookupStatus.FOUND, mx_records, attempt)

        if status_code == 3:  # NXDOMAIN: the domain itself does not exist
            return MxLookupResult(
                MxLookupStatus.NO_RECORDS, (), attempt, "authoritative NXDOMAIN"
            )
        # Authoritative NOERROR answer carrying zero MX records.
        return MxLookupResult(
            MxLookupStatus.NO_RECORDS, (), attempt, "authoritative answer, 0 MX records"
        )

    return MxLookupResult(
        MxLookupStatus.INDETERMINATE, (), _MX_ATTEMPTS, last_detail or "lookup failed"
    )



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
    # Set only when the critical MX check is *confirmed* to have failed.
    mx_failed = False

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

        # Live DNS MX check for corporate email domains (only with consent).
        if consent:
            mx = await _check_domain_mx(email_domain)
            if mx.status is MxLookupStatus.FOUND:
                if not any(rf.severity == Severity.HIGH for rf in risk_factors):
                    top_mx = mx.records[0].split()[-1]
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
            elif mx.status is MxLookupStatus.INDETERMINATE:
                # Rule 2 — a failed lookup is NOT evidence of missing mail
                # routing.  Enterprise domains get the explicit re-scan flag.
                enterprise = is_verified_enterprise_domain(email_domain)
                base_score += _MX_INDETERMINATE_PENALTY
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.RECRUITER_VERIFICATION,
                        severity=Severity.MEDIUM if enterprise else Severity.LOW,
                        description=(
                            "Network Timeout / Re-scan Required"
                            if enterprise
                            else "DNS MX lookup inconclusive — re-scan required"
                        ),
                        evidence=(
                            f"MX lookup for '{email_domain}' did not complete after "
                            f"{mx.attempts} attempts ({mx.detail}). No conclusion is drawn about "
                            "this domain's mail routing; a re-scan is required before any "
                            "verification status is assigned."
                        ),
                        source="dns_mx_verifier",
                        confidence=0.40,
                    )
                )
            else:
                # Rule 3 — positively confirmed: zero MX records.
                mx_failed = True
                base_score = max(base_score + _MX_FAILURE_BONUS, _MX_FAILURE_SCORE_FLOOR)
                risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.RECRUITER_VERIFICATION,
                        severity=Severity.HIGH,
                        description="Recruiter email domain has no DNS MX mail exchangers.",
                        evidence=(
                            f"Confirmed: domain '{email_domain}' authoritatively returned no active "
                            "DNS MX mail routing records. The mailbox can neither send nor receive "
                            "authentic enterprise mail — an absolute mail-infrastructure failure."
                        ),
                        source=CRITICAL_INFRA_FAILURE_SOURCE,
                        confidence=0.95,
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

    # Rule 1 — a failed critical MX check pivots the entire Recruiter
    # Verification section to FAIL.  Positive "verified" evidence lines are
    # dropped so the section can never read as both verified-safe and high risk.
    if mx_failed:
        risk_factors = [rf for rf in risk_factors if rf.severity != Severity.LOW]
        base_score = max(base_score, _MX_FAILURE_SCORE_FLOOR)

    final_score = round(min(max(base_score, 0.0), 100.0), 2)
    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)
