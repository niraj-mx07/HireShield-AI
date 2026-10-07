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
import uuid
from datetime import datetime, timezone
from typing import List, Optional


from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.database import get_database
from app.models.schemas import (
    AssessmentRequest,
    AssessmentResponse,
    AssessmentStatus,
    CategoryScore,
    Recommendation,
    RiskBand,
    RiskFactor,
    ScamReportRequest,
    ScamReportResponse,
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
    recruiter_phone: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    chat_transcript: Optional[str] = Form(None),
    message_log: Optional[str] = Form(None),
    consent_for_external_lookups: bool = Form(False),
) -> AssessmentResponse:
    """Create and run a new risk assessment with a document upload.

    Every text field the JSON endpoint accepts is also accepted here, so
    attaching a file never silently drops the other inputs the user provided.
    """
    document_bytes = await document.read()

    # Mirror the frontend's stated 10MB limit; an oversized upload is rejected
    # before any analysis work happens.
    if len(document_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Document exceeds the 10MB upload limit.",
        )

    request = AssessmentRequest(
        url=url,
        description=description,
        company_name=company_name,
        recruiter_email=recruiter_email,
        recruiter_name=recruiter_name,
        recruiter_phone=recruiter_phone,
        message=message,
        chat_transcript=chat_transcript,
        message_log=message_log,
        consent_for_external_lookups=consent_for_external_lookups,
    )

    return await run_assessment(
        request,
        document_bytes=document_bytes,
        document_filename=document.filename,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/assessments — list recent assessments
# ---------------------------------------------------------------------------

@router.get(
    "/assessments",
    summary="List recent assessments",
    description="Retrieve a paginated list of recent assessment summaries, ordered by newest first.",
)
async def list_assessments(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
):
    """List stored assessments with lightweight summary fields."""
    db = get_database()
    cursor = (
        db.assessments
        .find({}, {
            "_id": 0,
            "id": 1,
            "status": 1,
            "risk_score": 1,
            "risk_band": 1,
            "recommendation": 1,
            "confidence": 1,
            "active_inputs": 1,
            "input_summary": 1,
            "created_at": 1,
            "updated_at": 1,
        })
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    total = await db.assessments.count_documents({})

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "assessments": docs,
    }


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
        company_name=doc.get("company_name", "Unspecified Company"),
        job_title=doc.get("job_title", "Job Opportunity"),
        recruiter_name=doc.get("recruiter_name"),
        recruiter_contact=doc.get("recruiter_contact"),
        recruiter_email=doc.get("recruiter_email"),
        recruiter_phone=doc.get("recruiter_phone"),
        recruiter_linkedin=doc.get("recruiter_linkedin"),
        detected_sources=doc.get("detected_sources", []),
        category_scores=[CategoryScore(**cs) for cs in doc.get("category_scores", [])],
        risk_factors=[RiskFactor(**rf) for rf in doc.get("risk_factors", [])],
        active_inputs=doc.get("active_inputs", []),
        document_derived_inputs=doc.get("document_derived_inputs", []),
        created_at=doc.get("created_at"),
    )


# ---------------------------------------------------------------------------
# Community Scam Registry Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/scams/report",
    response_model=ScamReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a verified scam indicator",
    description="Submit a fraudulent UPI ID, recruiter phone number, Telegram handle, or email to the community blacklist.",
)
async def report_scam(report: ScamReportRequest) -> ScamReportResponse:
    """Submit a scam indicator to the community defense database."""
    db = get_database()
    report_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)

    doc = {
        "id": report_id,
        "indicator_type": report.indicator_type.strip().lower(),
        "indicator_value": report.indicator_value.strip().lower(),
        "company_impersonated": report.company_impersonated.strip() if report.company_impersonated else None,
        "description": report.description.strip(),
        "loss_amount": report.loss_amount,
        "reported_at": now,
    }
    await db.scam_reports.insert_one(doc)

    return ScamReportResponse(
        id=report_id,
        indicator_type=doc["indicator_type"],
        indicator_value=doc["indicator_value"],
        company_impersonated=doc["company_impersonated"],
        description=doc["description"],
        loss_amount=doc["loss_amount"],
        reported_at=now,
    )


@router.get(
    "/scams/lookup",
    summary="Lookup a potential scam indicator",
    description="Check whether a phone number, UPI handle, recruiter email, or Telegram handle exists in the scam blacklist.",
)
async def lookup_scam(
    indicator: str = Query(..., min_length=2, description="Indicator value to search (e.g. phone, UPI, email, handle)")
):
    """Search community blacklist for matches."""
    db = get_database()
    clean_val = indicator.strip().lower()
    
    # Case-insensitive substring search
    regex_query = {"indicator_value": {"$regex": clean_val, "$options": "i"}}
    matches = await db.scam_reports.find(regex_query).to_list(length=10)

    found = len(matches) > 0
    return {
        "found": found,
        "query": clean_val,
        "match_count": len(matches),
        "reports": [
            {
                "id": m["id"],
                "indicator_type": m["indicator_type"],
                "indicator_value": m["indicator_value"],
                "company_impersonated": m.get("company_impersonated"),
                "description": m["description"],
                "reported_at": m.get("reported_at"),
            }
            for m in matches
        ],
    }


@router.get(
    "/scams/recent",
    summary="Get recent community scam alerts",
    description="Fetch recent community-reported fraudulent recruitment attempts.",
)
async def get_recent_scams(limit: int = Query(10, ge=1, le=50)):
    """Fetch recent community scam reports."""
    db = get_database()
    cursor = db.scam_reports.find().sort("reported_at", -1).limit(limit)
    reports = await cursor.to_list(length=limit)

    return {
        "count": len(reports),
        "reports": [
            {
                "id": r["id"],
                "indicator_type": r["indicator_type"],
                "indicator_value": r["indicator_value"],
                "company_impersonated": r.get("company_impersonated"),
                "description": r["description"],
                "reported_at": r.get("reported_at"),
            }
            for r in reports
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_has_input(request: AssessmentRequest) -> None:
    """Ensure at least one meaningful input field is provided.

    ``message``, ``chat_transcript`` and ``message_log`` are first-class inputs
    to the scanning endpoint: a submission that carries only an email/chat
    payload must be analysed, not rejected with a 422.  Whitespace-only values
    count as absent.
    """
    if not any(
        (value or "").strip()
        for value in (
            request.url,
            request.description,
            request.company_name,
            request.recruiter_email,
            request.recruiter_name,
            request.recruiter_phone,
            request.message,
            request.chat_transcript,
            request.message_log,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "At least one input field (url, description, company_name, "
                "recruiter_email, recruiter_name, recruiter_phone, message, "
                "chat_transcript, or message_log) must be provided."
            ),
        )
