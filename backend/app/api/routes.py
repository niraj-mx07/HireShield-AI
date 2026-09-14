"""Assessment API routes.

Endpoints
---------
POST /api/v1/assessments
    Submit a new assessment via JSON body (URL / text / details).

POST /api/v1/assessments/upload
    Submit a new assessment with an attached document (multipart/form-data).

GET  /api/v1/assessments/{assessment_id}
    Retrieve a previously generated assessment report.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.database import get_database
from app.models.schemas import (
    AssessmentRequest,
    AssessmentResponse,
    AssessmentStatus,
    CategoryScore,
    Recommendation,
    RiskBand,
    RiskFactor,
)
from app.services.pipeline import run_assessment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["assessments"])


# ---------------------------------------------------------------------------
# POST /api/v1/assessments — JSON submission
# ---------------------------------------------------------------------------

@router.post(
    "/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new risk assessment",
    description=(
        "Submit a job/internship URL, description, company name, and/or "
        "recruiter details for risk analysis. Returns an explainable "
        "0–100 risk score with a recommendation."
    ),
)
async def create_assessment(request: AssessmentRequest) -> AssessmentResponse:
    """Create and run a new risk assessment from JSON input."""
    _validate_has_input(request)
    return await run_assessment(request)


# ---------------------------------------------------------------------------
# POST /api/v1/assessments/upload — multipart with document
# ---------------------------------------------------------------------------

@router.post(
    "/assessments/upload",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create assessment with document upload",
    description=(
        "Submit an assessment with an attached offer letter / PDF alongside "
        "optional text fields. The document is analysed for formatting "
        "anomalies, payment clauses, and consistency."
    ),
)
async def create_assessment_with_upload(
    document: UploadFile = File(..., description="Offer letter or PDF to analyse"),
    url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    recruiter_email: Optional[str] = Form(None),
    recruiter_name: Optional[str] = Form(None),
    consent_for_external_lookups: bool = Form(False),
) -> AssessmentResponse:
    """Create and run a new risk assessment with a document upload."""
    request = AssessmentRequest(
        url=url,
        description=description,
        company_name=company_name,
        recruiter_email=recruiter_email,
        recruiter_name=recruiter_name,
        consent_for_external_lookups=consent_for_external_lookups,
    )

    document_bytes = await document.read()
    return await run_assessment(
        request,
        document_bytes=document_bytes,
        document_filename=document.filename,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/assessments/{assessment_id}
# ---------------------------------------------------------------------------

@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentResponse,
    summary="Retrieve an assessment report",
    description="Look up a previously generated assessment by its ID.",
)
async def get_assessment(assessment_id: str) -> AssessmentResponse:
    """Retrieve a stored assessment by ID."""
    db = get_database()
    doc = await db.assessments.find_one({"id": assessment_id})

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found.",
        )

    return AssessmentResponse(
        id=doc["id"],
        status=AssessmentStatus(doc.get("status", "completed")),
        risk_score=doc.get("risk_score", 0.0),
        risk_band=RiskBand(doc.get("risk_band", "low")),
        recommendation=Recommendation(doc.get("recommendation", "HOLD")),
        confidence=doc.get("confidence", 0.0),
        category_scores=[CategoryScore(**cs) for cs in doc.get("category_scores", [])],
        risk_factors=[RiskFactor(**rf) for rf in doc.get("risk_factors", [])],
        created_at=doc.get("created_at"),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_has_input(request: AssessmentRequest) -> None:
    """Ensure at least one meaningful input field is provided."""
    if not any([
        request.url,
        request.description,
        request.company_name,
        request.recruiter_email,
        request.recruiter_name,
    ]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "At least one input field (url, description, company_name, "
                "recruiter_email, or recruiter_name) must be provided."
            ),
        )
