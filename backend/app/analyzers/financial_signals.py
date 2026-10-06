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
    (r"\b(?:refundable (?:deposit|fee|security|charge)|security (?:deposit|fee|charge)|caution deposit|laptop deposit|hardware deposit|equipment deposit)\b", "Security Deposit Demand"),
    (r"\b(?:training fee|training kit charge|certification fee|onboarding kit fee)\b", "Training Kit / Program Fee"),
    (r"\b(?:gate pass|id card charge|badge fee|uniform charge|medical test charge|bgv verification charge)\b", "Verification / Gate Pass Charge"),
    (r"\b(?:courier charge|shipping charge|customs fee|dispatch charge)\b", "Hardware Shipping / Courier Charge Trap"),
    (r"\b(?:cashier['’]?s?\s*check|reimbursement check|purchase.*portal|certified vendor portal)\b", "Cashier Check Equipment Scam"),
    (r"\b(?:prepaid task|task recharge|recharge.*wallet|daily payout.*guaranteed|task commission|like.*subscribe.*earn)\b", "Prepaid Investment / Task Scam"),
]


async def analyze(
    description: str | None = None,
    message: str | None = None,
    document_text: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Scan all text inputs for financial extortion and advance-fee scam clauses.

    Returns:
        A :class:`CategoryResult` with score (0–100), risk factors, and analyzed=True/False.
    """
    corpus_parts = [t.strip() for t in (description, message, document_text) if t and t.strip()]
    if not corpus_parts:
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    full_text = " ".join(corpus_parts)
    text_lower = full_text.lower()

    risk_factors: list[RiskFactor] = []
    base_score = 0.0

    # 1. Check for specific advance fee and deposit keywords
    for pattern, label in FEE_DEMAND_PATTERNS:
        match = re.search(pattern, text_lower)
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
    vpa_pat = r"\b([a-zA-Z0-9.\-_]{2,64}@(?!gmail|yahoo|outlook|hotmail|icloud|proton)[a-zA-Z]{2,32})\b"
    
    extracted_vpas = re.findall(vpa_pat, full_text, flags=re.IGNORECASE)
    has_upi_keyword = bool(re.search(upi_keywords_pat, text_lower))

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
    for pat in CRYPTO_PATTERNS:
        match = re.search(pat, text_lower)
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
    money_demand = re.search(r"(?:pay|transfer|deposit|send)\s*(?:rs\.?|inr|₹|\$)\s*(\d+[\d,]*)", text_lower)
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
    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)
