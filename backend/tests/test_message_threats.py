"""Tests for the Message & Transcript Analysis Engine.

Rule 1 — zero-tolerance chat-redirection gate: interview / onboarding
briefings pushed onto Telegram, Signal, WhatsApp or bare ``@handles`` raise a
sentinel factor that floors the overall score at 92+ and hard-codes
``DON'T APPLY``.

Rule 2 — full-payload financial scanning: every input field is scanned to its
final character for check / payout / upfront-payment hooks, which fail the
Financial Scam Check at 95+.

Rule 3 — only Microsoft Teams / Zoom / Webex invitations sent to a corporate
e-mail domain bypass the chat gate.
"""

from __future__ import annotations

import pytest

from app.analyzers import financial_signals
from app.models.schemas import (
    AssessmentRequest,
    CHAT_REDIRECT_GATE_SOURCE,
    CategoryResult,
    Recommendation,
    RiskBand,
    RiskCategory,
    RiskFactor,
    Severity,
)
from app.services import message_threats, pipeline, risk_engine


# ---------------------------------------------------------------------------
# Rule 1 — chat-redirection detection
# ---------------------------------------------------------------------------


def test_telegram_interview_redirection_detected():
    """Telegram + contact instruction + interview context raises a hit."""
    hit = message_threats.detect_chat_redirection(
        "Hi, your interview is scheduled for tomorrow. Please download "
        "Telegram and message our hiring manager @apex_hr_lead."
    )
    assert hit is not None
    assert hit.platform.lower() == "telegram"
    assert "telegram" in hit.evidence.lower()


def test_whatsapp_onboarding_briefing_detected():
    """WhatsApp as the onboarding-briefing channel raises a hit."""
    hit = message_threats.detect_chat_redirection(
        "Contact the HR team on WhatsApp for your onboarding briefing."
    )
    assert hit is not None
    assert hit.platform.lower() == "whatsapp"


def test_signal_directional_link_detected():
    """'… conducted over Signal' links the platform directionally."""
    hit = message_threats.detect_chat_redirection(
        "Your interview will be conducted over Signal."
    )
    assert hit is not None
    assert hit.platform.lower() == "signal"


def test_bare_handle_detected():
    """A bare @username contact handle counts as a redirection instruction."""
    hit = message_threats.detect_chat_redirection(
        "Your interview coordinator for this role is @sarah_talent."
    )
    assert hit is not None
    assert hit.platform.startswith("@")


def test_short_link_detected():
    """t.me / wa.me short links are anonymous chat-network pointers."""
    hit = message_threats.detect_chat_redirection(
        "Join our hiring group at t.me/acme_hiring to schedule your interview."
    )
    assert hit is not None
    assert "t.me" in hit.platform


def test_no_recruitment_context_is_not_a_hit():
    """A platform mention without hiring / onboarding framing is not a hit."""
    assert (
        message_threats.detect_chat_redirection(
            "Download the app to sync your calendar reminders."
        )
        is None
    )


def test_no_platform_is_not_a_hit():
    """Ordinary hiring text with no chat network raises nothing."""
    assert (
        message_threats.detect_chat_redirection(
            "Your interview is scheduled for Tuesday at 10 AM."
        )
        is None
    )


def test_empty_payload_is_not_a_hit():
    assert message_threats.detect_chat_redirection(None) is None
    assert message_threats.detect_chat_redirection("   \n\t  ") is None


# ---------------------------------------------------------------------------
# Rule 3 — enterprise video-platform bypass
# ---------------------------------------------------------------------------


def test_enterprise_video_with_corporate_email_bypasses_gate():
    """Teams/Zoom/Webex + corporate invitation domain => no gate."""
    hit = message_threats.detect_chat_redirection(
        "Your interview is on Zoom — reach me @sarah_talent. "
        "The calendar invite was sent to recruiting@acmecorp.com."
    )
    assert hit is None


def test_enterprise_video_with_personal_email_does_not_bypass():
    """A consumer mail domain is not a corporate invitation domain."""
    hit = message_threats.detect_chat_redirection(
        "Your interview is on Zoom — reach me @sarah_talent. "
        "The calendar invite was sent to sarah.talent@gmail.com."
    )
    assert hit is not None


def test_microsoft_teams_bypass_with_corporate_domain():
    assert (
        message_threats.detect_chat_redirection(
            "Briefing on Microsoft Teams — join as @hr_panelist. "
            "Invite from talent@acme-corp.com."
        )
        is None
    )


def test_enterprise_video_invitation_requires_both_halves():
    """Video platform without a corporate e-mail (and vice versa) fails."""
    assert (
        message_threats.has_enterprise_video_invitation(
            "Your interview is on Zoom tomorrow."
        )
        is False
    )
    assert (
        message_threats.has_enterprise_video_invitation(
            "Invite sent to recruiting@acmecorp.com."
        )
        is False
    )
    assert (
        message_threats.has_enterprise_video_invitation(
            "Zoom invite sent to recruiting@acmecorp.com."
        )
        is True
    )


# ---------------------------------------------------------------------------
# Rule 1 — risk engine hard gate
# ---------------------------------------------------------------------------


def _clean_results() -> dict[RiskCategory, CategoryResult]:
    """Every category analyzed and perfectly safe."""
    return {
        category: CategoryResult(score=0.0, risk_factors=[], analyzed=True)
        for category in RiskCategory
    }


def _gate_factor() -> RiskFactor:
    return RiskFactor(
        category=RiskCategory.RECRUITER_VERIFICATION,
        severity=Severity.HIGH,
        description="Hiring communication redirected to a personal chat network.",
        source=CHAT_REDIRECT_GATE_SOURCE,
        confidence=0.97,
    )


def test_gate_floors_score_at_92_and_forces_dont_apply():
    """Even with every other category clean, the gate decides the verdict."""
    results = _clean_results()
    results[RiskCategory.RECRUITER_VERIFICATION].risk_factors.append(_gate_factor())

    score, band, rec, _confidence, _scores, factors = risk_engine.score_assessment(results)

    assert score >= 92.0
    assert band is RiskBand.VERY_HIGH
    assert rec is Recommendation.DONT_APPLY
    assert any(rf.source == CHAT_REDIRECT_GATE_SOURCE for rf in factors)


def test_gate_cannot_be_averaged_down_by_thin_evidence():
    """Low raw scores + thin coverage still resolve to 92+ / DON'T APPLY."""
    results = {
        RiskCategory.RECRUITER_VERIFICATION: CategoryResult(
            score=15.0,
            analyzed=True,
            risk_factors=[_gate_factor()],
        ),
        RiskCategory.JOB_CONTENT: CategoryResult(
            score=5.0, risk_factors=[], analyzed=True
        ),
    }

    score, band, rec, _confidence, _scores, _factors = risk_engine.score_assessment(results)

    assert score >= 92.0
    assert band is RiskBand.VERY_HIGH
    assert rec is Recommendation.DONT_APPLY


def test_without_gate_the_verdict_is_unchanged():
    """Control: an identical low-risk assessment keeps its original verdict."""
    results = {
        RiskCategory.RECRUITER_VERIFICATION: CategoryResult(
            score=20.0, risk_factors=[], analyzed=True
        )
    }

    score, band, rec, _confidence, _scores, _factors = risk_engine.score_assessment(results)

    assert score == 20.0
    assert band is RiskBand.LOW
    assert rec is Recommendation.APPLY


# ---------------------------------------------------------------------------
# Rule 2 — full-payload financial scanning
# ---------------------------------------------------------------------------


async def _financial(**kwargs):
    return await financial_signals.analyze(**kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "trailing_clause",
    [
        "Onboarding is complete — funds arrive as your startup check",
        "Your reimbursement check will be dispatched after verification",
        "We will issue a certified check for the hardware purchase",
        "The equipment funds are already reserved for you",
        "Everything is verified and your first payout is queued",
        "Sign here and we will mail the check",
    ],
)
async def test_end_of_string_financial_hooks_fail_at_95(trailing_clause):
    """Hooks in the final sentence (down to the last char) fail the category."""
    result = await _financial(
        description="Senior data analyst role, fully remote.",
        message=trailing_clause,
    )
    assert result.analyzed is True
    assert result.score >= 95.0, f"{trailing_clause!r} scored {result.score}"
    assert any(
        rf.source == "full_payload_financial_hook_scanner"
        or rf.severity == Severity.HIGH
        for rf in result.risk_factors
    )


@pytest.mark.asyncio
async def test_reimbursement_framed_as_benefit_still_fails():
    """A 'benefit'-framed reimbursement check is still an advance-fee trap."""
    result = await _financial(
        message="As a sign-on benefit you will be reimbursed via a reimbursement check."
    )
    assert result.score >= 95.0


@pytest.mark.asyncio
async def test_benign_background_check_is_not_a_financial_hit():
    """Legitimate 'background check' wording must not fail the category."""
    result = await _financial(
        description=(
            "ACME runs a standard background check and reference check before "
            "joining. No fees are charged to candidates."
        )
    )
    assert result.analyzed is True
    assert result.score < 30.0, f"benign text scored {result.score}"
    assert not any(rf.severity == Severity.HIGH for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_benign_check_instruction_is_not_a_financial_hit():
    """'Please check your email' is an instruction, not a money instrument."""
    result = await _financial(
        message="Please check your email for the interview schedule."
    )
    assert result.score < 30.0, f"benign text scored {result.score}"


@pytest.mark.asyncio
async def test_chat_transcript_field_is_fully_scanned():
    """A hook living only in the transcript alias field still fails at 95+."""
    result = await _financial(
        description="Remote data entry role with weekly output reviews.",
        chat_transcript="Recruiter: perfect, all approved. Your startup check",
    )
    assert result.score >= 95.0


@pytest.mark.asyncio
async def test_clean_payload_stays_low():
    """Control: a clean payload keeps the informational score."""
    result = await _financial(
        description="Compensation: Rs 12,00,000 per annum + performance bonus.",
        message="Standard direct bank transfer after onboarding.",
    )
    assert result.score < 30.0


# ---------------------------------------------------------------------------
# Pipeline end-to-end — the three rules wired together
# ---------------------------------------------------------------------------


class _FakeCursor:
    """Minimal Motor cursor stand-in."""

    def __init__(self, items=None):
        self._items = list(items or [])

    async def to_list(self, length=None):
        return self._items[:length] if length is not None else self._items


class _FakeCollection:
    async def insert_one(self, document):
        return None

    async def update_one(self, flt, update):
        return None

    def find(self, _query):
        return _FakeCursor()


class _FakeDatabase:
    def __init__(self):
        self.assessments = _FakeCollection()
        self.scam_reports = _FakeCollection()


@pytest.fixture
def fake_db(monkeypatch):
    """Route pipeline database access to an in-memory double."""
    db = _FakeDatabase()
    monkeypatch.setattr(pipeline, "get_database", lambda: db)
    return db


def _category_score(response, category: RiskCategory) -> float:
    for entry in response.category_scores:
        if entry.category == category:
            return entry.score
    raise AssertionError(f"category {category} missing from response")


@pytest.mark.asyncio
async def test_pipeline_chat_redirection_gate_forces_dont_apply(fake_db):
    """A pasted transcript that redirects to Telegram yields 92+ / DON'T APPLY."""
    request = AssessmentRequest(
        chat_transcript=(
            "Recruiter: Your interview is confirmed for tomorrow.\n"
            "Please download Telegram and message our hiring manager "
            "@apex_hr_lead for the onboarding briefing."
        ),
    )

    response = await pipeline.run_assessment(request)

    assert response.risk_score >= 92.0, f"score was {response.risk_score}"
    assert response.recommendation is Recommendation.DONT_APPLY
    assert any(
        rf.source == CHAT_REDIRECT_GATE_SOURCE for rf in response.risk_factors
    )


@pytest.mark.asyncio
async def test_pipeline_whatsapp_message_key_raises_gate(fake_db):
    """The gate also fires when the transcript arrives under the message key."""
    request = AssessmentRequest(
        message="Contact the HR supervisor on WhatsApp before your interview.",
    )

    response = await pipeline.run_assessment(request)

    assert response.risk_score >= 92.0
    assert response.recommendation is Recommendation.DONT_APPLY


@pytest.mark.asyncio
async def test_pipeline_enterprise_video_bypass_avoids_gate(fake_db):
    """A Zoom invite to a corporate domain must NOT trigger the gate."""
    request = AssessmentRequest(
        chat_transcript=(
            "Recruiter: Your interview is on Zoom.\n"
            "Coordinator handle: @sarah_talent\n"
            "Calendar invite sent to recruiting@acmecorp.com."
        ),
    )

    response = await pipeline.run_assessment(request)

    assert not any(
        rf.source == CHAT_REDIRECT_GATE_SOURCE for rf in response.risk_factors
    )
    assert response.recommendation is not Recommendation.DONT_APPLY
    assert response.risk_score < 92.0


@pytest.mark.asyncio
async def test_pipeline_end_of_string_financial_hook_fails_category(fake_db):
    """A trailing 'startup check' sentence fails Financial Scam Check at 95+."""
    request = AssessmentRequest(
        message=(
            "Congratulations, you cleared every round. Verification complete; "
            "funds arrive as your startup check"
        ),
    )

    response = await pipeline.run_assessment(request)

    assert _category_score(response, RiskCategory.FINANCIAL_SCAM) >= 95.0
    assert response.recommendation is Recommendation.DONT_APPLY


