"""Financial / Scam Signals — category weight 15 %.

Detects registration fees, refundable deposits, UPI / QR code payment demands,
task investment traps, and advance cashier-check reimbursement clauses.
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
from app.services import negation_scope

logger = logging.getLogger(__name__)

# Specific monetary extraction patterns
UPI_PATTERNS = [
    r"\b(?:upi|gpay|google pay|phonepe|paytm|bhim|qr code|scanner|vpa)\b",
    r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}",  # typical UPI ID pattern like user@okaxis
]

CRYPTO_PATTERNS = [
    r"\b(?:crypto|bitcoin|usdt|trc20|erc20|binance|trust wallet|metamask|crypto wallet)\b",
    r"\b(?:wire transfer|western union|moneygram|gift card|apple gift card|steam card)\b",
]

FEE_DEMAND_PATTERNS = [
    (r"\b(?:registration fee|processing fee|application fee|interview fee|consultancy charge)\b", "Mandatory Application / Registration Fee"),
    (r"\b(?:refundable deposit|security deposit|caution deposit|laptop deposit|hardware deposit|equipment deposit)\b", "Security Deposit Demand"),
    (r"\b(?:training fee|training kit charge|certification fee|onboarding kit fee)\b", "Training Kit / Program Fee"),
    (r"\b(?:gate pass|id card charge|badge fee|uniform charge|medical test charge|bgv verification charge)\b", "Verification / Gate Pass Charge"),
    (r"\b(?:courier charge|shipping charge|customs fee|dispatch charge)\b", "Hardware Shipping / Courier Charge Trap"),
    (r"\b(?:cashier['’]?s?\s*check|reimbursement check|purchase.*portal|certified vendor portal)\b", "Cashier Check Equipment Scam"),
    (r"\b(?:prepaid task|task recharge|recharge.*wallet|daily payout.*guaranteed|task commission|like.*subscribe.*earn)\b", "Prepaid Investment / Task Scam"),
]

# ---------------------------------------------------------------------------
# Rule 2 — full-payload financial hooks (checks & upfront payments)
# ---------------------------------------------------------------------------
# These phrases frequently sit in the *final* sentence of a transcript or chat
# log.  Every pattern below is matched against the whole payload — the scan runs
# to the very last character, so trailing sentences can never escape
# verification.

_MONEY_HOOK_PATTERNS: list[tuple[str, str]] = [
    (
        r"\b(?:startup|cashier['’]?s?|certified|reimbursement|bonus|equipment|"
        r"refund|travel|sign(?:ing)?[\s-]?on|joining|insurance|activation|"
        r"processing|advance|company|official)\s+(?:check|cheque)s?\b",
        "Monetary 'check' instrument offered or requested",
    ),
    (
        r"\b(?:check|cheque)s?\s+(?:for|of|worth|valued?\s+at)\s*"
        r"(?:\$|₹|€|£|rs\.?|inr|\d)",
        "Currency-denominated 'check' referenced",
    ),
    (
        r"\b(?:equipment|hardware|relocation|sign(?:ing)?[\s-]?on|startup|bonus|"
        r"training|suppl(?:y|ies)|office)\s+(?:fund|funds|money|monies|advance|"
        r"allowance|reimburse\w*|payment)s?\b",
        "Upfront 'equipment funds' / advance framed as a benefit",
    ),
    (
        r"\b(?:upfront|advance|prepaid|pre-paid|prepayment|pre-payment|"
        r"down\s+payment|initial)\s+(?:payment|fee|charge|deposit|amount|cost|sum)s?\b",
        "Upfront payment demand",
    ),
    (
        r"\b(?:first|initial|your|guaranteed|daily|weekly|instant|immediate|quick|"
        r"fast|same[\s-]day)\s+payouts?\b",
        "Payout framed as an immediate benefit",
    ),
    (
        r"\bpayouts?\b(?!\s+(?:structure|schedule|terms|timeline|policy|ratio|date|"
        r"method|period|frequency|history|report|rate|options?|window))",
        "Payout hook in the message payload",
    ),
    (
        r"\b(?:money\s+order|bank\s+(?:draft|giro)|demand\s+draft|pay[\s-]order)\b",
        "Mail-order money instrument requested",
    ),
    (
        r"\b(?:mail\w*|send|deliver|issue|deposit|cashi\w*|encash\w*|wire)\b"
        r"[^.]{0,50}\b(?:check|cheque)s?\b",
        "Candidate asked to mail / receive a 'check'",
    ),
]

# Legitimate uses of the word "check" that carry no payment meaning — these
# must never fail the category on their own.
_MONEY_HOOK_COMPILED: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(p, re.IGNORECASE), label) for p, label in _MONEY_HOOK_PATTERNS
)

# Legitimate uses of the word "check" that carry no payment meaning — these
# must never fail the category on their own.
_BENIGN_CHECK_RE = re.compile(
    r"(?:"
    r"\b(?:background|reference|identity|kyc|security|health|medical|drug|"
    r"aptitude|skill|skills|technical|coding|qualification|vetting|verification|"
    r"control|quality|final|term|system|reality|fact|sanity|unit|integration|"
    r"smoke|regression|code|screening|interview|eligibility|police|credential|"
    r"degree|employment|criminal|professional|review|consistency|syntax|logic|"
    r"manual|automated|due\s+diligence|peer|design|compliance|audit|inspection|"
    r"status|list|policy|weather|thermostat|reality)\s+checks?\b"
    r"|(?:please\s+|kindly\s+|to\s+|double[\s-])?check(?:s|ed|ing)?\s+"
    r"(?:your|the|this|our|for|to|if|whether|out|up|again|details|email|inbox|"
    r"records?|status|availability|eligibility|requirements?)\b"
    r")",
    re.IGNORECASE,
)
_GENERIC_CHECK_RE = re.compile(r"\b(?:check|cheque)s?\b", re.IGNORECASE)

# Compiled once — the analyzers re-scan the payload on every assessment.
_FEE_DEMAND_COMPILED = tuple(
    (re.compile(p, re.IGNORECASE), label) for p, label in FEE_DEMAND_PATTERNS
)
_CRYPTO_COMPILED = tuple(re.compile(p, re.IGNORECASE) for p in CRYPTO_PATTERNS)

# Rule 2 — a check / upfront-payment demand pins this category to a hard fail.
_FORCED_FAIL_SCORE = 95.0


async def analyze(
    description: str | None = None,
    message: str | None = None,
    document_text: str | None = None,
    chat_transcript: str | None = None,
    message_log: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Scan all text inputs for financial extortion and advance-fee scam clauses.

    Rule 2: the *entire* payload is scanned — every field is joined and matched
    right up to its final character, so hooks hidden in trailing sentences of a
    pasted transcript (``startup check``, ``reimbursement check``, ``payout``,
    ``certified check``, ``equipment funds`` …) are never skipped.

Negation scope
--------------
Every matcher below is scoped through :mod:`app.services.negation_scope`.  A
keyword inside a *denied* clause is not evidence of a scam: ``"Infosys never
issues financial checks"`` and ``"we will never ask you to pay a registration
fee"`` are anti-fraud warnings, and scoring them as a fee demand or a
fake-check trap accuses a real employer.  Only a clause that *instructs or
performs* the payment counts.  The protection is clause-scoped, never global —
burying a real demand next to a disclaimer does not launder it.

    Returns:
        A :class:`CategoryResult` with score (0–100), risk factors, and analyzed=True/False.
    """
    corpus_parts = [
        t.strip()
        for t in (description, message, document_text, chat_transcript, message_log)
        if t and t.strip()
    ]
    if not corpus_parts:
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    full_text = " ".join(corpus_parts)
    text_lower = full_text.lower()

    risk_factors: list[RiskFactor] = []
    base_score = 0.0

    # 1. Check for specific advance fee and deposit keywords
    for pattern, label in _FEE_DEMAND_COMPILED:
        match = negation_scope.first_active_match(full_text, pattern)
        if match:
            base_score += 45.0
            # Extract snippet
            start = max(0, match.start() - 30)
            end = min(len(full_text), match.end() + 40)
            snippet = full_text[start:end].strip()

            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.FINANCIAL_SCAM,
                    severity=Severity.HIGH,
                    description=f"{label} detected in listing or communication.",
                    evidence=f"Clause detected: '...{snippet}...'. Legitimate employers never charge candidates money at any stage.",
                    source="financial_fee_pattern_scanner",
                    confidence=0.96,
                )
            )

    # 2. Check for UPI / Indian payment gateways & extract specific UPI VPA handle if present
    upi_keywords_pat = r"\b(?:upi|gpay|google pay|phonepe|paytm|bhim|qr code|scanner|vpa)\b"
    # UPI VPAs are bare handles (`name@okaxis`, `9812345678@paytm`) — a dotted
    # or hyphenated tail means a normal e-mail address, never a P2P handle.
    vpa_pat = r"\b([a-zA-Z0-9.\-_]{2,64}@(?!gmail|yahoo|outlook|hotmail|icloud|proton)[a-zA-Z]{2,32}(?![.\-]\w))\b"
    
    extracted_vpas = [
        m.group(1) for m in negation_scope.iter_active_matches(
            full_text, re.compile(vpa_pat, re.IGNORECASE)
        )
    ]
    has_upi_keyword = negation_scope.has_active_match(
        full_text, re.compile(upi_keywords_pat, re.IGNORECASE)
    )

    if extracted_vpas or has_upi_keyword:
        base_score += 40.0
        if extracted_vpas:
            vpa_display = ", ".join(extracted_vpas[:2])
            evidence_msg = (
                f"Personal peer-to-peer UPI VPA ID identified: '{vpa_display}'. "
                "Authentic corporate hiring never requests candidates to transfer funds to personal UPI handles."
            )
        else:
            evidence_msg = "Recruitment process mandates fund transfer via retail UPI, PhonePe, GPay, or Paytm."

        risk_factors.append(
            RiskFactor(
                category=RiskCategory.FINANCIAL_SCAM,
                severity=Severity.HIGH,
                description="Direct peer-to-peer payment method (UPI / GPay / PhonePe / Paytm / QR Code) requested.",
                evidence=evidence_msg,
                source="upi_payment_scanner",
                confidence=0.96 if extracted_vpas else 0.94,
            )
        )

    # 3. Check for Crypto / Wire / Gift Card payment requests
    has_crypto = False
    for pat in _CRYPTO_COMPILED:
        match = negation_scope.first_active_match(full_text, pat)
        if match:
            has_crypto = True
            break

    if has_crypto:
        base_score += 45.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.FINANCIAL_SCAM,
                severity=Severity.HIGH,
                description="High-risk untraceable payment method (Cryptocurrency, Wire, Gift Card) detected.",
                evidence="Communication requests transaction via cryptocurrency, wire transfer, or gift cards.",
                source="untraceable_payment_scanner",
                confidence=0.95,
            )
        )

    # 4. If monetary amounts (Rs, INR, $, ₹) are mentioned alongside "pay" or "transfer" or "deposit"
    money_demand = negation_scope.first_active_match(
        full_text,
        re.compile(r"(?:pay|transfer|deposit|send)\s*(?:rs\.?|inr|₹|\$)\s*(\d+[\d,]*)", re.IGNORECASE),
    )
    if money_demand and not any(rf.severity == Severity.HIGH for rf in risk_factors):
        base_score += 35.0
        amount = money_demand.group(0)
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.FINANCIAL_SCAM,
                severity=Severity.MEDIUM,
                description="Explicit monetary transfer request identified.",
                evidence=f"Text asks candidate to '{amount}' prior to onboarding.",
                source="monetary_demand_extractor",
                confidence=0.85,
            )
        )

    # 5. Rule 2 — full-payload scan for end-of-string financial hooks.  The
    #    patterns are matched against the whole joined payload, so a hook in
    #    the very last sentence of a transcript is caught exactly like one in
    #    the middle.  Nothing before the final character is skipped.
    hook_matches: list[re.Match[str]] = []
    for pattern, label in _MONEY_HOOK_COMPILED:
        match = negation_scope.first_active_match(full_text, pattern)
        if not match:
            continue
        hook_matches.append(match)
        base_score += 50.0
        start = max(0, match.start() - 30)
        end = min(len(full_text), match.end() + 40)
        snippet = full_text[start:end].strip()
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.FINANCIAL_SCAM,
                severity=Severity.HIGH,
                description=f"{label} in the full message payload.",
                evidence=(
                    f"Clause detected: '...{snippet}...'. A check, payout, or upfront "
                    "payment framed as a benefit or reimbursement is an advance-fee "
                    "trap — legitimate employers never route money through candidates."
                ),
                source="full_payload_financial_hook_scanner",
                confidence=0.97,
            )
        )

    # 6. Any remaining bare "check" / "cheque" that is not a benign collocation
    #    ("background check", "please check your email") and was not already
    #    covered by a named hook above counts as a monetary-instrument mention.
    benign_spans = [m.span() for m in _BENIGN_CHECK_RE.finditer(text_lower)]
    hook_spans = [m.span() for m in hook_matches]
    for match in _GENERIC_CHECK_RE.finditer(text_lower):
        if any(lo <= match.start() and match.end() <= hi for lo, hi in hook_spans):
            continue
        if any(lo <= match.start() and match.end() <= hi for lo, hi in benign_spans):
            continue
        # "Infosys never issues financial checks" — a denied reference to a
        # monetary instrument is a warning about the scam, not the scam.
        if negation_scope.is_passive_reference(text_lower, match.start(), match.end()):
            continue
        base_score += 45.0
        start = max(0, match.start() - 30)
        end = min(len(full_text), match.end() + 40)
        snippet = full_text[start:end].strip()
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.FINANCIAL_SCAM,
                severity=Severity.HIGH,
                description="Monetary 'check' / 'cheque' mentioned in the message payload.",
                evidence=(
                    f"Clause detected: '...{snippet}...'. A check issued to a candidate "
                    "is a fake-check / funds-withdrawal trap."
                ),
                source="full_payload_financial_hook_scanner",
                confidence=0.93,
            )
        )
        break  # one representative clause is enough to fail the category

    # 4. If text was scanned and clean of financial demands
    if not risk_factors:
        base_score = 5.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.FINANCIAL_SCAM,
                severity=Severity.LOW,
                description="No advance fee, deposit, or monetary payment demands detected.",
                evidence="Text is free of registration fees, kit deposits, and peer-to-peer payment requests.",
                source="financial_fee_pattern_scanner",
                confidence=0.90,
            )
        )

    final_score = round(min(max(base_score, 0.0), 100.0), 2)

    # Rule 2 — a confirmed check or upfront-payment demand fails this category
    # outright: the score is pinned at 95+ and can never be scored down, even
    # when the clause is framed as a benefit or reimbursement.
    if final_score < _FORCED_FAIL_SCORE and any(
        rf.severity == Severity.HIGH for rf in risk_factors
    ):
        final_score = _FORCED_FAIL_SCORE

    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)
