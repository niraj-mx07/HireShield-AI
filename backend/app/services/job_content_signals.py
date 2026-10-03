"""Behavioural signal extraction for the job-content risk classifier.

This module encodes the classification policy used by
:mod:`app.analyzers.job_content`:

1. **Neutralise legal nouns and enterprise brands.**  Standard legal corporate
   suffixes (``Pvt``, ``Ltd``, ``Inc``, ``Corp``), geographic indicators
   (``India`` …) and the brand names scammers impersonate (``Tata``, ``TCS``,
   ``Consultancy Services``, ``Google``, ``Amazon`` …) carry no fraud signal on
   their own.  :func:`neutralize_text` strips them before the text classifier
   runs so that they can never act as risk weights ("brand poisoning").

2. **Escalate on behaviour, not vocabulary.**  :func:`detect_behavioral_signals`
   reports only explicit deceptive mechanics: advance-fee demands, fake-check
   equipment loops, chat-only hiring channels, and grossly inflated pay.

3. **Contextual override.**  A listing that documents a standard corporate
   hiring structure *and* states that no recruitment fee is charged is treated
   as safe (:func:`has_corporate_structure` / :func:`has_explicit_no_fee`).

Nothing in this module asserts fraud as fact; it returns *indicators* only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schemas import Severity

# ---------------------------------------------------------------------------
# Neutralised vocabulary — legal suffixes, geographic indicators, brands
# ---------------------------------------------------------------------------

# Standard legal corporate suffixes and geographic indicators: always neutral.
LEGAL_AND_GEO_TERMS: tuple[str, ...] = (
    "pvt", "private", "private limited", "ltd", "limited", "llp", "llc",
    "inc", "incorporated", "corp", "corporation", "co", "company",
    "gmbh", "plc", "pcs", "opc",
    "india", "indian", "bharat",
    "bengaluru", "bangalore", "mumbai", "navi mumbai", "delhi", "new delhi",
    "hyderabad", "pune", "chennai", "kolkata", "noida", "gurgaon", "gurugram",
    "ahmedabad", "jaipur", "kochi", "coimbatore",
)

# Enterprises scammers impersonate.  Presence alone is neutral; only a
# deceptive behaviour paired with a brand escalates risk.
IMPERSONATED_BRANDS: tuple[str, ...] = (
    "tata", "tata consultancy services", "tata group", "tcs",
    "consultancy services", "infosys", "wipro", "cognizant", "hcl", "hcltech",
    "tech mahindra", "accenture", "capgemini", "deloitte", "kpmg", "pwc",
    "pricewaterhousecoopers", "ernst & young", "ey", "ibm", "oracle", "sap",
    "salesforce", "google", "alphabet", "amazon", "aws", "microsoft", "apple",
    "meta", "facebook", "netflix", "nvidia", "adobe", "intel", "qualcomm",
    "cisco", "dell", "flipkart", "reliance", "jio", "razorpay", "swiggy",
    "zomato", "paytm", "phonepe", "byju's", "ola", "uber", "linkedin",
    "naukri", "goldman sachs", "jpmorgan", "morgan stanley", "hsbc", "citi",
    "barclays", "stripe",
)


def _compile_lexicon(terms: tuple[str, ...]) -> re.Pattern[str]:
    """Build a case-insensitive alternation regex with word-boundary guards.

    Terms are de-duplicated, stripped of trailing periods, and sorted longest
    first so multi-word phrases (``private limited``) win over their prefixes
    (``private``).
    """
    cleaned = {t.strip().lower().rstrip(".") for t in terms if t and t.strip()}
    alternatives = "|".join(re.escape(t) for t in sorted(cleaned, key=len, reverse=True))
    # (?<![A-Za-z0-9]) / (?![A-Za-z0-9]) rather than \b so phrases containing
    # spaces and '&' anchor correctly.
    return re.compile(rf"(?<![A-Za-z0-9])(?:{alternatives})(?![A-Za-z0-9])", re.IGNORECASE)


_NEUTRALISE_RE = _compile_lexicon(LEGAL_AND_GEO_TERMS + IMPERSONATED_BRANDS)


def neutralize_text(text: str) -> str:
    """Remove legal suffixes, geographic indicators, and brand names.

    The masked tokens are replaced with a single space so that unknown
    (out-of-vocabulary) n-grams contribute zero weight to the TF-IDF model.
    """
    if not text:
        return ""
    return _NEUTRALISE_RE.sub(" ", text)


# ---------------------------------------------------------------------------
# Behavioural signal data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BehavioralSignal:
    """A single explicit deceptive mechanic found in the text."""

    label: str
    severity: Severity
    description: str
    evidence: str
    source: str
    confidence: float


# ---------------------------------------------------------------------------
# Negation guard — "never charges any ... fee" is NOT an advance-fee demand
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"[.!?\n;]+")
_NEGATION_RE = re.compile(
    r"\b(?:no|not|never|without|zero|nil|free|neither|nor)\b", re.IGNORECASE
)
# A payment *action* between the negation and the fee noun re-asserts the
# demand ("no hidden charges, just pay the registration fee").  Noun forms such
# as "security deposit" are deliberately excluded: they appear inside the very
# negated list ("never charges ... or security deposit") and must not unlock it.
_PAYMENT_VERB_RE = re.compile(
    r"\b(?:pay|pays|paid|paying|send|sends|sent|remit|remits|transfer|transferred|"
    r"wire|submit|submits|top\s*up|recharge|recharges)\b",
    re.IGNORECASE,
)


def _is_negated(text: str, match_start: int) -> bool:
    """Return ``True`` when the clause leading up to ``match_start`` negates it.

    Only the current sentence is inspected.  A negation cue that is separated
    from the match by a payment verb does not count (the demand is still live).
    """
    sentence_start = 0
    for boundary in _SENTENCE_SPLIT_RE.finditer(text[:match_start]):
        sentence_start = boundary.end()

    prefix = text[sentence_start:match_start]
    cues = list(_NEGATION_RE.finditer(prefix))
    if not cues:
        return False

    tail = prefix[cues[-1].end():]
    return not _PAYMENT_VERB_RE.search(tail)


# ---------------------------------------------------------------------------
# Rule 3 — explicit fraudulent mechanics (behaviour, never vocabulary)
# ---------------------------------------------------------------------------

# Advance-fee / deposit demands.  Each entry is (regex, human label).
_ADVANCE_FEE_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"\b(?:registration|processing|application|interview|consultancy|placement|"
        r"enrol{0,2}ment|enroll{0,2}ment)\s*(?:fee|fees|charge|charges|amount)\b",
        "Application / registration fee",
    ),
    (
        r"\b(?:refundable|security|caution|laptop|hardware|equipment|onboarding|"
        r"training)\s*deposit\b",
        "Refundable / security deposit",
    ),
    (
        r"\b(?:training|onboarding|certification|interview|documentation)\s*"
        r"(?:kit\s*)?(?:fee|fees|charge|charges|cost)\b",
        "Paid training / onboarding kit",
    ),
    (
        r"\b(?:gate\s*pass|id\s*card|badge|uniform|medical|bgv|"
        r"background\s*verification)\s*(?:fee|fees|charge|charges|cost)\b",
        "Verification / gate-pass charge",
    ),
    (
        r"\b(?:courier|shipping|customs|dispatch|documentation)\s*"
        r"(?:fee|fees|charge|charges)\b",
        "Courier / documentation charge",
    ),
    (
        r"\b(?:prepaid\s*task|task\s*recharge|recharge\b[^.]{0,20}?\bwallet|"
        r"wallet\s*recharge|top\s*up\b[^.]{0,20}?\bwallet)\b",
        "Prepaid task / wallet recharge trap",
    ),
)

# Fake-check equipment loop ("we'll mail you a check to buy hardware …").
_CHECK_LOOP_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"\b(?:mail|send|sends|sent|issue|issues|provide|provides|post|courier|"
        r"dispatch|receive|receives|expect)\s+(?:you\s+|us\s+|me\s+)?"
        r"(?:a\s+|the\s+|your\s+)?(?:(?:rs\.?|inr|₹|\$)\s*)?(?:\d[\d,]*\s*)?"
        r"(?:company\s+|certified\s+|bank\s+)?(?:cashier'?s?\s+)?(?:check|cheque)\b",
        "Cheque mailed to the candidate",
    ),
    (
        r"\b(?:check|cheque)\b[^.]{0,48}?\b(?:buy|purchase|order|procure|acquire)\b",
        "Cheque tied to an equipment purchase",
    ),
    (
        r"\b(?:buy|purchase|order|procure|acquire)\b[^.]{0,60}?\b(?:equipment|hardware|"
        r"laptop|device|devices|supplies|software|furniture)\b[^.]{0,60}?"
        r"\b(?:vendor|portal|supplier)\b",
        "Equipment bought via a designated vendor portal",
    ),
    (
        r"\b(?:certified|designated|approved|official|company|our)\s+"
        r"(?:vendor|supplier)\s+portal\b",
        "'Certified vendor' portal",
    ),
)

# Unofficial communication channels for enterprise hiring.
_CHAT_CHANNEL_RE = re.compile(
    r"\b(?:telegram|whatsapp|signal|viber|imo|discord|wa\.me|t\.me|"
    r"chat\s+on|dm\s+on)\b",
    re.IGNORECASE,
)
_CHAT_STRONG_CONTEXT_RE = re.compile(
    r"\b(?:interview\w*|hiring|recruit\w*|selection|selected|shortlist\w*|"
    r"onboard\w*|screening|hr\s+round|supervisor|task\s+assignment\w*)\b",
    re.IGNORECASE,
)
_CHAT_WEAK_CONTEXT_RE = re.compile(
    r"\b(?:contact|reach|message|chat|dm|apply|join|talk|coordinate|reply)\b",
    re.IGNORECASE,
)
_CHAT_EXCLUSIVE_RE = re.compile(
    r"\b(?:only|exclusively|entirely|solely|no\s+calls?|no\s+official\s+email|"
    r"instead\s+of\s+email)\b",
    re.IGNORECASE,
)

# Grossly inflated compensation benchmarks.
_MONEY_FREQ_RE = re.compile(
    r"(?:rs\.?|inr|₹|\$|usd)?\s*(\d[\d,]{2,})\s*\+?\s*(?:per|\/|a|each|every)\s*(week|day)\b",
    re.IGNORECASE,
)
_HIGH_FREQ_WINDOW_RE = re.compile(
    r"\b(?:daily|weekly|monthly|per\s+(?:week|day)|a\s+week|a\s+day)\b",
    re.IGNORECASE,
)
_LOW_BARRIER_RE = re.compile(
    r"\b(?:no\s+experience|no\s+skills?|no\s+interview|any\s+degree|10th\s+pass|"
    r"12th\s+pass|freshers?|no\s+qualification|without\s+experience|no\s+skills?\s+required)\b",
    re.IGNORECASE,
)

# Grossly inflated weekly / daily benchmarks: ₹25,000+/week, ₹5,000+/day.
_WEEKLY_THRESHOLD = 25_000
_DAILY_THRESHOLD = 5_000



# ---------------------------------------------------------------------------
# Rule 4 — contextual override helpers
# ---------------------------------------------------------------------------

# Standard corporate hiring structure: rounds, assessments, background checks.
_CORPORATE_STRUCTURE_PATTERNS: tuple[str, ...] = (
    r"\b(?:interview\s+rounds?|rounds?\s+of\s+interviews?|multiple\s+rounds?|"
    r"technical\s+interview|hr\s+interview|panel\s+interview|structured\s+interview)\b",
    r"\b(?:aptitude|cognitive|online|written|technical|skills|coding)\s+"
    r"(?:test|assessment|round)\b",
    r"\b(?:background\s+(?:check|verification|screening)|bgv|reference\s+"
    r"(?:check|verification)|police\s+verification)\b",
    r"\b(?:job\s+description|key\s+responsibilities|responsibilities|"
    r"qualifications|eligibility\s+criteria|job\s+requirements)\b",
    r"\b(?:careers?\s+(?:page|portal|site|website)|official\s+(?:careers|website)|"
    r"applicant\s+tracking|application\s+portal)\b",
    r"\b(?:probation\s+period|notice\s+period|employment\s+agreement|offer\s+letter|"
    r"health\s+benefits|401\s*\(?k\)?)\b",
)

# Explicit "we never charge candidates" statements.
_NO_FEE_PATTERNS: tuple[str, ...] = (
    r"\b(?:no|zero|without\s+any)\s+(?:registration|application|processing|"
    r"recruitment|interview|training|placement)?\s*fees?\b",
    r"\b(?:never|does\s+not|do\s+not|doesn'?t|don'?t|will\s+not|won'?t)\s+"
    r"(?:charge|charges|ask|asks|require|requires|collect|collects|demand|"
    r"demands|take|takes)\b[^.]{0,48}?\b(?:fee|fees|money|payment|payments|"
    r"deposit|charge|charges|amount)\b",
    r"\b(?:free\s+of\s+cost|at\s+no\s+cost|no\s+cost\s+to\s+(?:the\s+)?candidate|"
    r"free\s+of\s+charge|absolutely\s+free)\b",
    r"\b(?:fees?\s+(?:are|is)\s+not\s+(?:charged|required|applicable|collected))\b",
    r"\b(?:do\s+not|don'?t|never)\s+pay\b",
)

_COMPILED_CORPORATE = tuple(re.compile(p, re.IGNORECASE) for p in _CORPORATE_STRUCTURE_PATTERNS)
_COMPILED_NO_FEE = tuple(re.compile(p, re.IGNORECASE) for p in _NO_FEE_PATTERNS)


def has_corporate_structure(text: str) -> bool:
    """``True`` when the text documents a standard corporate hiring process."""
    if not text:
        return False
    return any(p.search(text) for p in _COMPILED_CORPORATE)


def has_explicit_no_fee(text: str) -> bool:
    """``True`` when the text explicitly states that no fee is charged."""
    if not text:
        return False
    return any(p.search(text) for p in _COMPILED_NO_FEE)


def _snippet(text: str, start: int, end: int, pad: int = 60) -> str:
    """Return a single-line evidence snippet around a match."""
    s = max(0, start - 30)
    e = min(len(text), end + pad)
    return text[s:e].strip().replace("\n", " ")



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_behavioral_signals(text: str) -> list[BehavioralSignal]:
    """Detect explicit deceptive mechanics in ``text``.

    Only behavioural risk is reported.  Neutral corporate vocabulary (legal
    suffixes, geographic indicators, brand names) never produces a signal —
    that is exactly what :func:`neutralize_text` removes before classification.

    Returns a list of :class:`BehavioralSignal` (possibly empty).
    """
    if not text or not text.strip():
        return []

    signals: list[BehavioralSignal] = []

    # 1) Advance-fee / deposit demands (negation-aware)
    fee_labels: list[str] = []
    fee_evidence = ""
    for pattern, label in _ADVANCE_FEE_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            if _is_negated(text, m.start()):
                continue
            if label not in fee_labels:
                fee_labels.append(label)
                if not fee_evidence:
                    fee_evidence = _snippet(text, m.start(), m.end())
    if fee_labels:
        signals.append(
            BehavioralSignal(
                label="Advance-fee demand",
                severity=Severity.HIGH,
                description=(
                    "Listing or communication demands payment from the applicant "
                    "before or during hiring (" + "; ".join(fee_labels) + ")."
                ),
                evidence=(
                    f"Clause detected: '…{fee_evidence}…'. Legitimate employers never "
                    "charge candidates money at any stage of the hiring process."
                ),
                source="behavioral_advance_fee",
                confidence=0.96,
            )
        )

    # 2) Fake-check equipment loop
    check_labels: list[str] = []
    check_evidence = ""
    for pattern, label in _CHECK_LOOP_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m and not _is_negated(text, m.start()):
            if label not in check_labels:
                check_labels.append(label)
                if not check_evidence:
                    check_evidence = _snippet(text, m.start(), m.end())
    if check_labels:
        signals.append(
            BehavioralSignal(
                label="Fake-check equipment loop",
                severity=Severity.HIGH,
                description=(
                    "Candidate is told a cheque will be sent so they can buy equipment "
                    "from a designated/vendor portal (" + "; ".join(check_labels) + ")."
                ),
                evidence=(
                    f"Clause detected: '…{check_evidence}…'. This matches the classic "
                    "fake-cheque / equipment-overpayment pattern."
                ),
                source="behavioral_check_loop",
                confidence=0.93,
            )
        )


    # 3) Unofficial communication channel for hiring
    channel = _CHAT_CHANNEL_RE.search(text)
    if channel:
        strong = bool(_CHAT_STRONG_CONTEXT_RE.search(text))
        weak = bool(_CHAT_WEAK_CONTEXT_RE.search(text))
        exclusive = bool(_CHAT_EXCLUSIVE_RE.search(text))
        channel_severity: Severity | None = None
        conf = 0.0
        if strong or (weak and exclusive):
            channel_severity, conf = Severity.HIGH, 0.90
        elif exclusive:
            channel_severity, conf = Severity.MEDIUM, 0.80
        if channel_severity is not None:
            signals.append(
                BehavioralSignal(
                    label="Unofficial hiring channel",
                    severity=channel_severity,
                    description=(
                        "Hiring communication is routed through a personal chat app "
                        f"('{channel.group(0)}') rather than official corporate channels."
                    ),
                    evidence=(
                        "Channel reference detected: "
                        f"'…{_snippet(text, channel.start(), channel.end(), 40)}…'."
                    ),
                    source="behavioral_unofficial_channel",
                    confidence=conf,
                )
            )

    # 4) Grossly inflated compensation benchmarks
    comp_severity: Severity | None = None
    comp_evidence = ""
    for m in _MONEY_FREQ_RE.finditer(text):
        amount = int(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        threshold = _WEEKLY_THRESHOLD if unit.startswith("week") else _DAILY_THRESHOLD
        if amount >= threshold:
            comp_severity = Severity.HIGH
            comp_evidence = _snippet(text, m.start(), m.end())
            break
    if comp_severity is None:
        for m in re.finditer(r"\bguaranteed\b", text, re.IGNORECASE):
            window = text[max(0, m.start() - 40): m.end() + 40]
            if _HIGH_FREQ_WINDOW_RE.search(window):
                comp_severity = (
                    Severity.HIGH if _LOW_BARRIER_RE.search(text) else Severity.MEDIUM
                )
                comp_evidence = _snippet(text, m.start(), m.end())
                break
    if comp_severity is not None:
        signals.append(
            BehavioralSignal(
                label="Grossly inflated compensation",
                severity=comp_severity,
                description=(
                    "Daily/weekly pay promise is far above market norms for the stated "
                    "role and skill level."
                ),
                evidence=f"Compensation clause detected: '…{comp_evidence}…'.",
                source="behavioral_inflated_compensation",
                confidence=0.90 if comp_severity is Severity.HIGH else 0.75,
            )
        )

    return signals

