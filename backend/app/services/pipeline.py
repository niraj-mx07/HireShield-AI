"""Assessment Pipeline Orchestrator.

Coordinates the full analysis flow:

1. Run all analyzer modules (currently stubbed).
2. Feed results into the risk engine.
3. Persist the assessment record to MongoDB.
4. Return the structured response.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.analyzers import (
    company_verification,
    consistency_check,
    document_analysis,
    financial_signals,
    job_content,
    recruiter_verification,
    url_analysis,
)
from app.database import get_database
from app.models.schemas import (
    AssessmentRecord,
    AssessmentRequest,
    AssessmentResponse,
    AssessmentStatus,
    CategoryResult,
    RiskCategory,
)
from app.services.risk_engine import score_assessment
from app.utils.privacy import build_input_summary, redact_pii

logger = logging.getLogger(__name__)


async def run_assessment(
    request: AssessmentRequest,
    document_bytes: Optional[bytes] = None,
    document_filename: Optional[str] = None,
) -> AssessmentResponse:
    """Execute the full assessment pipeline for a submission.

    Args:
        request: Validated assessment input.
        document_bytes: Raw bytes of an uploaded file (if any).
        document_filename: Original filename of the uploaded file.

    Returns:
        A fully populated :class:`AssessmentResponse`.
    """
    assessment_id = uuid.uuid4().hex
    consent = request.consent_for_external_lookups

    logger.info(
        "Starting assessment %s — inputs: %s",
        assessment_id,
        redact_pii(str(build_input_summary(
            url=request.url,
            description=request.description,
            company_name=request.company_name,
            recruiter_email=request.recruiter_email,
            recruiter_name=request.recruiter_name,
            has_document=document_bytes is not None,
        ))),
    )

    # ------------------------------------------------------------------
    # 1. Create a pending record in the database
    # ------------------------------------------------------------------
    db = get_database()
    input_summary = build_input_summary(
        url=request.url,
        description=request.description,
        company_name=request.company_name,
        recruiter_email=request.recruiter_email,
        recruiter_name=request.recruiter_name,
        has_document=document_bytes is not None,
    )
    record = AssessmentRecord(id=assessment_id, input_summary=input_summary)
    await db.assessments.insert_one(record.model_dump())

    # ------------------------------------------------------------------
    # 2. Run all analyzers
    # ------------------------------------------------------------------
    results: dict[RiskCategory, CategoryResult] = {}

    results[RiskCategory.JOB_CONTENT] = await job_content.analyze(
        description=request.description,
        company_name=request.company_name,
    )
    results[RiskCategory.COMPANY_VERIFICATION] = await company_verification.analyze(
        company_name=request.company_name,
        url=request.url,
        consent=consent,
    )
    results[RiskCategory.RECRUITER_VERIFICATION] = await recruiter_verification.analyze(
        recruiter_email=request.recruiter_email,
        recruiter_name=request.recruiter_name,
        company_name=request.company_name,
        consent=consent,
    )
    results[RiskCategory.URL_WEBSITE] = await url_analysis.analyze(
        url=request.url,
        company_name=request.company_name,
        consent=consent,
    )
    results[RiskCategory.FINANCIAL_SCAM] = await financial_signals.analyze(
        description=request.description,
    )
    results[RiskCategory.DOCUMENT_ANALYSIS] = await document_analysis.analyze(
        document_bytes=document_bytes,
        document_filename=document_filename,
    )
    results[RiskCategory.INFORMATION_CONSISTENCY] = await consistency_check.analyze(
        description=request.description,
        url=request.url,
        company_name=request.company_name,
        recruiter_email=request.recruiter_email,
    )

    # ------------------------------------------------------------------
    # 3. Aggregate via risk engine
    # ------------------------------------------------------------------
    risk_score, band, rec, confidence, category_scores, risk_factors = score_assessment(results)

    # ------------------------------------------------------------------
    # 4. Build response and update the DB record
    # ------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    response = AssessmentResponse(
        id=assessment_id,
        status=AssessmentStatus.COMPLETED,
        risk_score=risk_score,
        risk_band=band,
        recommendation=rec,
        confidence=confidence,
        category_scores=category_scores,
        risk_factors=risk_factors,
        created_at=now,
    )

    await db.assessments.update_one(
        {"id": assessment_id},
        {"$set": {
            "status": AssessmentStatus.COMPLETED.value,
            "risk_score": risk_score,
            "risk_band": band.value,
            "recommendation": rec.value,
            "confidence": confidence,
            "category_scores": [cs.model_dump() for cs in category_scores],
            "risk_factors": [rf.model_dump() for rf in risk_factors],
            "updated_at": now.isoformat(),
        }},
    )

    logger.info(
        "Assessment %s completed — score=%.1f band=%s rec=%s confidence=%.2f",
        assessment_id, risk_score, band.value, rec.value, confidence,
    )
    return response
