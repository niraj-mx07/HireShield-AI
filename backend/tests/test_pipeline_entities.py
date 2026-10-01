"""End-to-end tests for the assessment pipeline's retrieval + NER wiring.

An in-memory fake database and stubbed network helpers keep these tests fully
offline: they assert that extracted entities are surfaced on the response (and
never persisted) and that external page retrieval is consent-gated and
performed exactly once per assessment.
"""

from __future__ import annotations

import pytest

from app.models.schemas import AssessmentRequest, AssessmentStatus
from app.services import pipeline


# ---------------------------------------------------------------------------
# In-memory database doubles
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


@pytest.fixture
def offline_analyzers(monkeypatch):
    """Stub the remaining third-party lookups so no network I/O occurs."""
    from app.analyzers import url_analysis

    async def fake_rdap(_domain):
        return None

    monkeypatch.setattr(url_analysis, "_check_domain_rdap", fake_rdap)


# ---------------------------------------------------------------------------
# Entity extraction is surfaced (and not persisted)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_includes_extracted_entities(fake_db):
    """Identifiers in the submitted text are returned on the response."""
    request = AssessmentRequest(
        description="Contact hr.team@acme-jobs.com or +91 98765 43210 before applying.",
    )

    response = await pipeline.run_assessment(request)

    labels = {entity.label for entity in response.entities}
    assert "EMAIL" in labels
    assert "PHONE" in labels
    assert response.status == AssessmentStatus.COMPLETED


@pytest.mark.asyncio
async def test_entities_are_never_persisted(fake_db):
    """Extracted PII stays in the response and is excluded from the DB write."""
    request = AssessmentRequest(description="Email hr.team@acme-jobs.com for details.")

    await pipeline.run_assessment(request)

    assert fake_db.assessments.inserted
    assert fake_db.assessments.updated
    _flt, update = fake_db.assessments.updated[-1]
    assert "entities" not in update["$set"]


@pytest.mark.asyncio
async def test_assessment_with_no_text_has_no_entities(fake_db):
    """An assessment without free text yields an empty entity list."""
    response = await pipeline.run_assessment(
        AssessmentRequest(company_name="Acme Recruiters Hub")
    )

    assert response.entities == []


# ---------------------------------------------------------------------------
# Consent-gated page retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_page_retrieval_is_consent_gated(fake_db, offline_analyzers, monkeypatch):
    """Without consent the pipeline never calls the retrieval service."""
    from app.services import web_retrieval

    async def boom(*_args, **_kwargs):
        raise AssertionError("page retrieval must be consent-gated")

    monkeypatch.setattr(web_retrieval, "fetch_page", boom)

    response = await pipeline.run_assessment(
        AssessmentRequest(
            url="https://careers-acme-groups.example.org/apply",
            description="Exciting remote data entry role. Apply now.",
            consent_for_external_lookups=False,
        )
    )

    assert response.status == AssessmentStatus.COMPLETED


@pytest.mark.asyncio
async def test_consented_assessment_fetches_page_exactly_once(
    fake_db, offline_analyzers, monkeypatch
):
    """One consent-gated fetch is shared across job-content and company checks."""
    from app.services import web_retrieval

    calls: list[str] = []

    async def fake_fetch(url, **_kwargs):
        calls.append(url)
        return web_retrieval.PageExtraction(
            url=url,
            final_url=url,
            domain="careers-acme-groups.example.org",
            status_code=200,
            text="Job description: data entry. Requirements: 40 wpm. Apply now.",
            has_job_posting=True,
        )

    monkeypatch.setattr(web_retrieval, "fetch_page", fake_fetch)

    response = await pipeline.run_assessment(
        AssessmentRequest(
            url="https://careers-acme-groups.example.org/apply",
            company_name="Acme Recruiters Hub",
            description="Remote data entry role, apply now.",
            consent_for_external_lookups=True,
        )
    )

    assert calls == ["https://careers-acme-groups.example.org/apply"]
    assert response.status == AssessmentStatus.COMPLETED


@pytest.mark.asyncio
async def test_controlled_retrieval_failure_does_not_break_assessment(
    fake_db, offline_analyzers, monkeypatch
):
    """A failing fetch degrades gracefully instead of aborting the run."""
    from app.services import web_retrieval

    async def failing_fetch(_url, **_kwargs):
        return None

    monkeypatch.setattr(web_retrieval, "fetch_page", failing_fetch)

    response = await pipeline.run_assessment(
        AssessmentRequest(
            url="https://careers-acme-groups.example.org/apply",
            description="Remote data entry role, apply now.",
            consent_for_external_lookups=True,
        )
    )

    assert response.status == AssessmentStatus.COMPLETED
