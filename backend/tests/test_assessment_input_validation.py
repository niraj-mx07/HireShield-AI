"""Tests for the scanning endpoint's input validation and payload aliasing.

An assessment may be submitted through three different text shapes:

* ``description`` / ``message`` — the canonical payload variables the
  analyzers read.
* ``chat_transcript`` / ``message_log`` — accepted alias keys that must pass
  the "at least one field provided" check and be folded into the canonical
  variable whenever the canonical one is empty.

Regression coverage for the Email/Message tab, which submits ``message`` on its
own and previously fell foul of the 422 rule.

Everything runs offline: pipeline tests route database access through an
in-memory double and never enable consent-gated external lookups.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.routes import _validate_has_input
from app.models.schemas import (
    AssessmentRequest,
    AssessmentStatus,
    normalize_text_payloads,
)
from app.services import pipeline


# ---------------------------------------------------------------------------
# In-memory database doubles (mirrors test_pipeline_entities)
# ---------------------------------------------------------------------------


class _FakeCursor:
    """Minimal Motor cursor stand-in."""

    def __init__(self, items=None):
        self._items = list(items or [])

    async def to_list(self, length=None):
        return self._items[:length] if length is not None else self._items


class _FakeCollection:
    """Records writes so tests can assert what was persisted."""

    def __init__(self):
        self.inserted: list[dict] = []
        self.updated: list[tuple[dict, dict]] = []

    async def insert_one(self, document):
        self.inserted.append(document)

    async def update_one(self, flt, update):
        self.updated.append((flt, update))

    def find(self, _query):
        return _FakeCursor()


class _FakeDatabase:
    """Only the collections the pipeline actually touches."""

    def __init__(self):
        self.assessments = _FakeCollection()
        self.scam_reports = _FakeCollection()


@pytest.fixture
def fake_db(monkeypatch):
    """Route pipeline database access to an in-memory double."""
    db = _FakeDatabase()
    monkeypatch.setattr(pipeline, "get_database", lambda: db)
    return db


TRANSCRIPT = (
    "Recruiter: Your application is approved! Send the $2,000 joining fee "
    "via UPI to confirm your slot."
)


# ---------------------------------------------------------------------------
# 422 "at least one field" rules
# ---------------------------------------------------------------------------


def _passes(request: AssessmentRequest) -> bool:
    """True when the request clears the 422 gate."""
    try:
        _validate_has_input(request)
    except HTTPException as exc:
        assert exc.status_code == 422
        return False
    return True


def test_no_input_at_all_is_rejected():
    """An empty body is still a 422."""
    with pytest.raises(HTTPException) as excinfo:
        _validate_has_input(AssessmentRequest())

    assert excinfo.value.status_code == 422


def test_error_detail_lists_the_new_alias_keys():
    """The 422 message names every key a client may legitimately send."""
    with pytest.raises(HTTPException) as excinfo:
        _validate_has_input(AssessmentRequest())

    detail = excinfo.value.detail
    for field in (
        "url",
        "description",
        "company_name",
        "recruiter_email",
        "recruiter_name",
        "message",
        "chat_transcript",
        "message_log",
    ):
        assert field in detail, f"{field} missing from 422 detail: {detail}"


@pytest.mark.parametrize(
    "field",
    [
        "url",
        "description",
        "company_name",
        "recruiter_email",
        "recruiter_name",
        "recruiter_phone",
        "message",
        "chat_transcript",
        "message_log",
    ],
)
def test_each_supported_field_alone_passes_validation(field):
    """Any single supported key satisfies the "at least one" check."""
    assert _passes(AssessmentRequest(**{field: "sample value"}))


def test_message_only_submission_is_not_rejected():
    """Regression: the Email/Message tab submits ``message`` and nothing else."""
    assert _passes(AssessmentRequest(message="Send the fee to confirm your slot."))


def test_whitespace_only_values_do_not_count_as_input():
    """A field full of whitespace is not a provided field."""
    with pytest.raises(HTTPException):
        _validate_has_input(
            AssessmentRequest(description="   ", message="\n\t", chat_transcript=" ")
        )


# ---------------------------------------------------------------------------
# Alias → canonical payload mapping
# ---------------------------------------------------------------------------


def test_chat_transcript_fills_empty_description():
    """An alias alone becomes the main payload the text engine reads."""
    request = AssessmentRequest(chat_transcript="Transcript body")

    folded = normalize_text_payloads(request)

    assert folded == ["chat_transcript"]
    assert request.description == "Transcript body"


def test_chat_transcript_never_overwrites_a_real_description():
    """Submitted input always wins over an alias."""
    request = AssessmentRequest(
        description="Real description", chat_transcript="Transcript body"
    )

    assert normalize_text_payloads(request) == []
    assert request.description == "Real description"
    assert request.chat_transcript == "Transcript body"


def test_message_log_fills_empty_message():
    request = AssessmentRequest(message_log="Log body")

    folded = normalize_text_payloads(request)

    assert folded == ["message_log"]
    assert request.message == "Log body"


def test_message_log_never_overwrites_a_real_message():
    request = AssessmentRequest(message="Real message", message_log="Log body")

    assert normalize_text_payloads(request) == []
    assert request.message == "Real message"


def test_blank_canonical_field_is_treated_as_empty():
    """Whitespace in ``description`` must not block the alias from landing."""
    request = AssessmentRequest(description="   ", chat_transcript="Transcript body")

    normalize_text_payloads(request)

    assert request.description == "Transcript body"


def test_no_aliases_reported_when_none_supplied():
    request = AssessmentRequest(url="https://example.com/job")

    assert normalize_text_payloads(request) == []


# ---------------------------------------------------------------------------
# End-to-end through the pipeline (offline)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_transcript_only_produces_a_report(fake_db):
    """A transcript-only submission is analysed and reported honestly."""
    request = AssessmentRequest(chat_transcript=TRANSCRIPT)

    response = await pipeline.run_assessment(request)

    assert response.status is AssessmentStatus.COMPLETED
    # The alias landed in the variable the text processing engine reads.
    assert request.description == TRANSCRIPT
    assert "Chat Transcript" in response.active_inputs
    assert "Job Description" not in response.active_inputs

    summary = fake_db.assessments.inserted[0]["input_summary"]
    assert summary["chat_transcript_provided"] is True
    assert summary["description_length"] == len(TRANSCRIPT)


@pytest.mark.asyncio
async def test_message_only_submission_produces_a_report(fake_db):
    """Regression for the Email/Message tab's 422."""
    request = AssessmentRequest(message=TRANSCRIPT)

    response = await pipeline.run_assessment(request)

    assert response.status is AssessmentStatus.COMPLETED
    assert "Email / Message" in response.active_inputs


@pytest.mark.asyncio
async def test_message_log_only_folds_into_message(fake_db):
    request = AssessmentRequest(message_log=TRANSCRIPT)

    response = await pipeline.run_assessment(request)

    assert response.status is AssessmentStatus.COMPLETED
    assert request.message == TRANSCRIPT
    assert "Email / Message" in response.active_inputs
    assert "Message Log" not in response.active_inputs

    summary = fake_db.assessments.inserted[0]["input_summary"]
    assert summary["message_log_provided"] is True


@pytest.mark.asyncio
async def test_description_and_transcript_are_reported_separately(fake_db):
    """When both arrive, neither is dropped and both are listed."""
    request = AssessmentRequest(
        description="Senior engineer role at Acme.",
        chat_transcript=TRANSCRIPT,
    )

    response = await pipeline.run_assessment(request)

    assert response.status is AssessmentStatus.COMPLETED
    assert request.description == "Senior engineer role at Acme."
    assert "Job Description" in response.active_inputs
    assert "Chat Transcript" in response.active_inputs

