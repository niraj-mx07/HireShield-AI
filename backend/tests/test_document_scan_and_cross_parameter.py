"""Tests for document scan calibration and cross-parameter entity extraction."""

import pytest
import pytest_asyncio

from app.database import connect, disconnect
from app.models.schemas import AssessmentRequest, RiskCategory, Severity
from app.services.pipeline import run_assessment
from app.analyzers import document_analysis


@pytest_asyncio.fixture(autouse=True)
async def db_lifecycle():
    await connect()
    yield
    await disconnect()


@pytest.mark.asyncio
async def test_scam_document_gives_high_risk_score():
    """Verify that an offer letter demanding a security deposit yields high risk (>= 60), not 5."""
    scam_doc = (
        "OFFER OF APPOINTMENT\n"
        "We are pleased to offer you the position of Data Entry Operator.\n"
        "Candidate must pay a refundable security deposit of Rs 5000 for training kit via UPI.\n"
        "Contact HR manager on Telegram @career_helpdesk immediately."
    )
    req = AssessmentRequest()
    res = await run_assessment(req, document_bytes=scam_doc.encode("utf-8"), document_filename="offer.txt")
    
    assert res.risk_score >= 60.0
    assert res.risk_band.value in ("high", "very_high")
    assert any("deposit" in rf.description.lower() for rf in res.risk_factors)
    assert any("telegram" in rf.description.lower() or "chat" in rf.description.lower() for rf in res.risk_factors)


@pytest.mark.asyncio
async def test_non_employment_document_flagged_moderate_risk():
    """Verify that uploading an irrelevant non-job document is flagged and does not get score 5."""
    unrelated_doc = (
        "Project Report on Photosynthesis in Plants.\n"
        "Chlorophyll absorbs light mostly in the blue and red regions of the spectrum.\n"
        "This experimental observation explains the rate of oxygen release."
    )
    req = AssessmentRequest()
    res = await run_assessment(req, document_bytes=unrelated_doc.encode("utf-8"), document_filename="biology_report.txt")
    
    # Lacks employment terms, should have moderate uncertainty, not flat 5
    assert res.risk_score > 15.0
    doc_cat = next(cs for cs in res.category_scores if cs.category == RiskCategory.DOCUMENT_ANALYSIS)
    assert any("lacks recognizable employment" in rf.description.lower() for rf in doc_cat.risk_factors)


@pytest.mark.asyncio
async def test_cross_parameter_extraction_from_document():
    """Verify that company name, recruiter email, and URL embedded in a document are extracted and analyzed."""
    doc_content = (
        "APPOINTMENT LETTER — INFOSYS LIMITED\n"
        "Company: Infosys Limited\n"
        "We are pleased to offer you employment as Systems Engineer.\n"
        "Annual CTC breakdown includes basic pay, Provident Fund, gratuity, and medical insurance.\n"
        "Please confirm your acceptance by emailing hr.talent@infosys.com.\n"
        "Portal: https://career.infosys.com/job/12345\n"
        "Registered Office: Electronics City, Hosur Road, Bangalore. CIN: L85110KA1981PLC013115."
    )
    # User provides ONLY the document, no separate URL/Company/Recruiter inputs
    req = AssessmentRequest()
    res = await run_assessment(req, document_bytes=doc_content.encode("utf-8"), document_filename="infosys_offer.txt")

    # Document should be low risk with genuine statutory clauses
    assert res.risk_score < 25.0
    
    # Categories should be analyzed because entities were extracted
    comp_cat = next(cs for cs in res.category_scores if cs.category == RiskCategory.COMPANY_VERIFICATION)
    assert comp_cat.analyzed is True

    rec_cat = next(cs for cs in res.category_scores if cs.category == RiskCategory.RECRUITER_VERIFICATION)
    assert rec_cat.analyzed is True

    url_cat = next(cs for cs in res.category_scores if cs.category == RiskCategory.URL_WEBSITE)
    assert url_cat.analyzed is True

    job_cat = next(cs for cs in res.category_scores if cs.category == RiskCategory.JOB_CONTENT)
    assert job_cat.analyzed is True
