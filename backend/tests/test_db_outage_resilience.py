"""Regression test: assessments survive a down/unreachable database.

Covers the localhost "Analysis unavailable — no report was generated.
NetworkError" outage: backend/.env pointed at an Atlas URI whose
credentials fail (OperationFailure: bad auth), and every DB write in the
pipeline was unguarded, so POST /api/v1/assessments returned 500 even
though the analyzers themselves work fine.  The pipeline must now treat
persistence as best-effort and still return a full report.
"""

from __future__ import annotations

import pytest

from app.models.schemas import AssessmentRequest, AssessmentStatus
from app.services import pipeline


class _FailingCollection:
    async def insert_one(self, document):  # pragma: no cover - always fails
        raise ConnectionError("simulated MongoDB outage")

    async def update_one(self, flt, update):  # pragma: no cover - always fails
        raise ConnectionError("simulated MongoDB outage")

    def find(self, *args, **kwargs):
        raise ConnectionError("simulated MongoDB outage")


class _FailingDatabase:
    def __init__(self):
        self.assessments = _FailingCollection()
        self.scam_reports = _FailingCollection()


@pytest.fixture
def failing_db(monkeypatch):
    """Route pipeline database access to an always-failing double."""
    db = _FailingDatabase()
    monkeypatch.setattr(pipeline, "get_database", lambda: db)
    return db


@pytest.mark.asyncio
async def test_url_assessment_survives_db_outage(failing_db, monkeypatch):
    """A URL-only scan returns COMPLETED when MongoDB is unreachable."""
    from app.analyzers import url_analysis

    async def fake_rdap(_domain):
        return None

    monkeypatch.setattr(url_analysis, "_check_domain_rdap", fake_rdap)

    response = await pipeline.run_assessment(
        AssessmentRequest(
            url="https://example.com/jobs/software-engineer",
            description="Senior software engineer role. Apply via our careers portal.",
            consent_for_external_lookups=False,
        )
    )

    assert response.status is AssessmentStatus.COMPLETED
    assert response.risk_score >= 0
    assert any(cs.category == "url_website" for cs in response.category_scores)


@pytest.mark.asyncio
async def test_uninitialised_db_still_returns_report(monkeypatch):
    """Even get_database() raising (never connected) must not 500 the scan."""
    def _boom():
        raise RuntimeError("Database not initialised. Ensure connect() is called at startup.")

    monkeypatch.setattr(pipeline, "get_database", _boom)

    response = await pipeline.run_assessment(
        AssessmentRequest(url="https://careers.example.org/apply")
    )

    assert response.status is AssessmentStatus.COMPLETED
