"""Regression tests for the negation-scope (inverse logic) fix.

The bug these pin shut: keyword matchers scored **protective disclaimers** as
**fraud mechanics**.  A flawless Infosys anti-fraud notice — *"Infosys never
issues financial checks"* / *"never conducts interviews over anonymous chat
applications such as WhatsApp"* — was reported as ``DON'T APPLY (80/100)`` with
a HIGH "financial scam 97" factor and a HIGH chat-redirection gate.

The fix must satisfy **both** halves of the contract:

1. A passive, protective warning is never a HIGH finding.
2. An active demand stays a HIGH finding — even when an attacker buries it next
   to a disclaimer.  This is why the guard is clause-scoped and not a global
   "if a disclaimer exists, PASS" override.
"""

from __future__ import annotations

import re

import pytest

from app.analyzers import document_analysis, financial_signals, job_content
from app.models.schemas import Severity
from app.services import message_threats, negation_scope
from app.services.job_content_signals import detect_behavioral_signals


# ---------------------------------------------------------------------------
# The reported document — a legitimate corporate anti-scam notice.
# Line wrapping is deliberate: PDF/DOCX extraction hard-wraps text, and the
# wrap point falls right before "WhatsApp".
# ---------------------------------------------------------------------------

INFOSYS_NOTICE = """Infosys Limited - Talent Acquisition Notice

Dear Candidate,

Thank you for your interest in the Software Engineer role at Infosys.

Infosys never issues financial checks, demand drafts, or pays equipment
advances to applicants at any stage of the recruitment process. We will never
ask you to pay a registration fee, interview fee, or any other charge in order
to process your application.

Infosys never conducts interviews over anonymous chat applications such as
WhatsApp, Telegram, or Signal. All interviews are conducted either on campus or
through the official Infosys careers portal. We will never share employee login
credentials and we never ask you to add our HR team on any personal messaging
handle.

If anyone contacts you claiming to represent Infosys and asks for money, that is
a fraud attempt. Please report it to fraud@infosys.com immediately.

Regards,
Talent Acquisition
"""

INFOSYS_DESCRIPTION = (
    "Software Engineer role at Infosys Limited, Bengaluru. "
    "Background verification required after the offer letter."
)


def _high_factors(result):
    return [rf for rf in result.risk_factors if rf.severity == Severity.HIGH]


# ---------------------------------------------------------------------------
# 1. The reported false positive is gone
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_infosys_notice_scores_no_high_financial_factor():
    """Financial category must PASS on a disclaimer-only notice."""
    result = await financial_signals.analyze(
        description=INFOSYS_DESCRIPTION, document_text=INFOSYS_NOTICE
    )
    assert result.analyzed is True
    assert _high_factors(result) == [], [rf.description for rf in _high_factors(result)]
    assert result.score < 10.0, result.score


@pytest.mark.asyncio
async def test_infosys_notice_produces_no_high_job_content_factor():
    """Job content must not report an advance-fee or chat-channel mechanic."""
    result = await job_content.analyze(
        description=INFOSYS_DESCRIPTION,
        company_name="Infosys",
        document_text=INFOSYS_NOTICE,
    )
    assert result.analyzed is True
    assert _high_factors(result) == [], [rf.description for rf in _high_factors(result)]
    assert result.score < 15.0, result.score


@pytest.mark.asyncio
async def test_infosys_notice_scores_no_high_document_factor():
    """Document analysis must not report a deposit or informal-channel clause."""
    result = await document_analysis.analyze(
        document_text=INFOSYS_NOTICE, document_filename="notice.txt"
    )
    assert result.analyzed is True
    assert _high_factors(result) == [], [rf.description for rf in _high_factors(result)]
    assert result.score < 10.0, result.score


def test_infosys_notice_does_not_raise_the_chat_redirection_gate():
    """The hard 92+ DON'T-APPLY gate must not fire on a denial clause."""
    assert message_threats.detect_chat_redirection(INFOSYS_NOTICE) is None


def test_infosys_notice_produces_no_behavioral_signals():
    assert detect_behavioral_signals(INFOSYS_NOTICE) == []


# ---------------------------------------------------------------------------
# 2. Active mechanics named in the mandate still fail
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "We will mail you a certified check of $800 to purchase equipment.",
        "Download the app from the link below and add our username to start.",
        "Kindly message us within 24 hours or your offer will lapse.",
        "Transfer Rs 5000 to the vendor portal before your interview.",
    ],
)
def test_instructional_action_keywords_remain_active(text):
    """'download', 'add username', 'within x hours', 'will mail you a check'."""
    pattern = re.compile(
        r"(?:check|cheque|download|add|within|transfer|pay|message|send|mail)",
        re.IGNORECASE,
    )
    assert negation_scope.has_active_match(text, pattern)


@pytest.mark.asyncio
async def test_real_check_scam_still_scores_high():
    """A genuine fake-check equipment loop must still fail hard."""
    result = await financial_signals.analyze(
        description="Marketing Executive, Work From Home, no experience needed.",
        message=(
            "Congratulations! We will send you a cashier's check of 500,000 rupees "
            "to buy the equipment kit. Deposit it in our vendor portal within 48 hours."
        ),
    )
    assert result.analyzed is True
    assert _high_factors(result), "a real fake-check loop must produce a HIGH factor"
    assert result.score >= 95.0


@pytest.mark.asyncio
async def test_real_whatsapp_redirection_still_raises_the_gate():
    """A live WhatsApp redirection must still hard-gate the verdict."""
    text = (
        "Hi, I am the HR manager. Please download our hiring app, add me on "
        "WhatsApp and message us within 2 hours for your interview briefing."
    )
    hit = message_threats.detect_chat_redirection(text)
    assert hit is not None
    assert "whatsapp" in hit.platform.lower()


# ---------------------------------------------------------------------------
# 3. Evasion guard — a disclaimer must not launder a real demand
# ---------------------------------------------------------------------------

EVASION_CASES = [
    (
        "disclaimer in a separate sentence",
        "Infosys never issues financial checks and never asks for fees. "
        "Pay Rs 5000 to hr@okaxis to activate your offer letter.",
    ),
    (
        "contrastive connective",
        "We never charge candidates any fee, however you must pay a refundable "
        "deposit of Rs 5000 before joining.",
    ),
    (
        "imperative after the denial",
        "We do not ask for money. Please send the registration fee of Rs 2500 "
        "to 9812345678@paytm today.",
    ),
    (
        "directive appended after a soft newline",
        "We never ask for a registration fee\n"
        "Download the app and pay Rs 5000 to activate your employee ID.",
    ),
]


@pytest.mark.parametrize("label, text", EVASION_CASES, ids=[c[0] for c in EVASION_CASES])
def test_disclaimer_does_not_launder_an_adjacent_demand(label, text):
    pattern = re.compile(
        r"(?:deposit|registration fee|pay\s+rs|send|download|\d{4,}@)", re.IGNORECASE
    )
    assert negation_scope.has_active_match(text, pattern), label


@pytest.mark.asyncio
async def test_fee_buried_next_to_a_disclaimer_still_fails_the_category():
    result = await financial_signals.analyze(
        description="Business Development Executive, Work From Home.",
        message=(
            "Infosys never issues financial checks and never asks candidates for "
            "fees. You must pay a refundable security deposit of Rs 5000 and send "
            "the payment receipt to 9812345678@paytm within 24 hours."
        ),
    )
    assert _high_factors(result), "a real deposit demand must survive the disclaimer"
    assert result.score >= 95.0


# ---------------------------------------------------------------------------
# 4. Unit-level scope behaviour
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text, keyword, expected_passive",
    [
        # passive — the speaker denies or forbids the mechanic
        ("Infosys never issues financial checks.", "checks", True),
        ("We never ask you to pay a registration fee.", "registration fee", True),
        ("No deposit is payable at any stage.", "deposit", True),
        ("Financial checks are never issued by us.", "checks", True),
        ("There is no requirement to pay a fee.", "pay a fee", True),
        ("Beware of fraudsters who ask for registration fees.", "registration fees", True),
        # active — the speaker performs or instructs the mechanic
        ("We issue financial checks on joining.", "checks", False),
        ("You must pay a registration fee to apply.", "registration fee", False),
        ("No hidden charges, just pay the registration fee of Rs 5000.",
         "registration fee", False),
        ("We never charge fees, but you must pay a deposit of Rs 5000.",
         "deposit", False),
        ("We never ask for fees. Please pay Rs 5000 to hr@okaxis.",
         "pay rs 5000", False),
        ("We will mail you a check for the equipment.", "check", False),
        ("Message us within 24 hours or the offer lapses.", "within 24 hours", False),
        ("Add our username to continue.", "add our username", False),
        ("Download the app to complete onboarding.", "download the app", False),
    ],
)
def test_is_passive_reference(text, keyword, expected_passive):
    start = text.lower().index(keyword)
    assert negation_scope.is_passive_reference(text, start, start + len(keyword)) is expected_passive


def test_a_denial_in_one_sentence_does_not_reach_the_next():
    """Sentence scope is what stops 'we never ask for fees. Pay Rs 5000.'"""
    text = "We never ask for fees. Send Rs 5000 to hr@okaxis."
    start = text.index("Send Rs 5000")
    assert negation_scope.is_passive_reference(text, start, start + 12) is False


def test_hard_wrapped_lines_stay_one_sentence():
    """A wrap point before a proper noun must not hide the governing denial."""
    text = "Infosys never conducts interviews over anonymous chat applications such as\nWhatsApp."
    start = text.index("WhatsApp")
    assert negation_scope.is_passive_reference(text, start, start + len("WhatsApp")) is True


def test_blank_line_is_a_hard_boundary():
    text = "We never ask for fees.\n\nSend Rs 5000 to hr@okaxis."
    start = text.index("Send Rs 5000")
    assert negation_scope.is_passive_reference(text, start, start + 12) is False