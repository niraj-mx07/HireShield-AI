"""Tests for document analysis module."""

from __future__ import annotations

import pytest
from app.analyzers import document_analysis
from app.models.schemas import Severity


@pytest.mark.asyncio
async def test_scam_text_in_document():
    """Test extracted text from offer letter containing fee demands yields high risk."""
    doc_text = "OFFER LETTER\nTo claim your joining kit, candidate must deposit fee of Rs 5000 refundable security deposit to bank account below."
    result = await document_analysis.analyze(document_text=doc_text)
    assert result.analyzed is True
    assert result.score >= 50.0
    assert any(rf.severity == Severity.HIGH for rf in result.risk_factors)


@pytest.mark.asyncio
async def test_legitimate_document_text():
    """Test legitimate document text returns low risk."""
    doc_text = "OFFER OF EMPLOYMENT\nWe are pleased to offer you the role of Software Engineer at Acme Corp. Annual compensation is $120,000."
    result = await document_analysis.analyze(document_text=doc_text)
    assert result.analyzed is True
    assert result.score < 30.0


@pytest.mark.asyncio
async def test_empty_document_unanalyzed():
    """Test empty document text returns analyzed=False."""
    result = await document_analysis.analyze(document_text="")
    assert result.analyzed is False
