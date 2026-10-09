"""Assessment Pipeline Orchestrator.

Coordinates the full analysis flow:

1. Run all analyzer modules (currently stubbed).
2. Feed results into the risk engine.
3. Persist the assessment record to MongoDB.
4. Return the structured response.
"""

from __future__ import annotations

import asyncio
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
    RiskBand,
    RiskCategory,
    RiskFactor,
    Severity,
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
            recruiter_phone=request.recruiter_phone,
            message=request.message,
            has_document=document_bytes is not None,
        ))),
    )

    # ------------------------------------------------------------------
    # 1. Create a pending record in the database
    # ------------------------------------------------------------------
    db = None
    try:
        db = get_database()
        input_summary = build_input_summary(
            url=request.url,
            description=request.description,
            company_name=request.company_name,
            recruiter_email=request.recruiter_email,
            recruiter_name=request.recruiter_name,
            recruiter_phone=request.recruiter_phone,
            message=request.message,
            has_document=document_bytes is not None,
        )
        record = AssessmentRecord(
            id=assessment_id,
            input_summary=input_summary,
            user_id=request.user_id,
            user_email=request.user_email.strip().lower() if request.user_email else None,
        )
        await asyncio.wait_for(db.assessments.insert_one(record.model_dump()), timeout=4.0)
    except Exception as exc:
        logger.warning("Database write skipped/timed out for pending assessment %s: %s", assessment_id, exc)

    # ------------------------------------------------------------------
    # 2. Extract Document Text (if any) and Run All Analyzers in Parallel
    # ------------------------------------------------------------------
    from app.analyzers.document_analysis import extract_document_text
    extracted_doc_text = extract_document_text(document_bytes, document_filename)

    (
        job_res,
        comp_res,
        rec_res,
        url_res,
        fin_res,
        doc_res,
        cons_res,
    ) = await asyncio.gather(
        job_content.analyze(
            description=request.description,
            company_name=request.company_name,
            message=request.message,
        ),
        company_verification.analyze(
            company_name=request.company_name,
            url=request.url,
            consent=consent,
        ),
        recruiter_verification.analyze(
            recruiter_email=request.recruiter_email,
            recruiter_name=request.recruiter_name,
            recruiter_phone=request.recruiter_phone,
            company_name=request.company_name,
            message=request.message,
            consent=consent,
        ),
        url_analysis.analyze(
            url=request.url,
            company_name=request.company_name,
            consent=consent,
        ),
        financial_signals.analyze(
            description=request.description,
            message=request.message,
            document_text=extracted_doc_text,
        ),
        document_analysis.analyze(
            document_bytes=document_bytes,
            document_filename=document_filename,
            document_text=extracted_doc_text,
        ),
        consistency_check.analyze(
            description=request.description,
            url=request.url,
            company_name=request.company_name,
            recruiter_email=request.recruiter_email,
            message=request.message,
            document_text=extracted_doc_text,
        ),
    )

    results: dict[RiskCategory, CategoryResult] = {
        RiskCategory.JOB_CONTENT: job_res,
        RiskCategory.COMPANY_VERIFICATION: comp_res,
        RiskCategory.RECRUITER_VERIFICATION: rec_res,
        RiskCategory.URL_WEBSITE: url_res,
        RiskCategory.FINANCIAL_SCAM: fin_res,
        RiskCategory.DOCUMENT_ANALYSIS: doc_res,
        RiskCategory.INFORMATION_CONSISTENCY: cons_res,
    }

    # ------------------------------------------------------------------
    # 2b. Cross-reference community scam blacklist
    # ------------------------------------------------------------------
    try:
        query_candidates = [
            v.strip().lower() for v in (
                request.recruiter_email,
                request.recruiter_phone,
                request.url,
            ) if v and v.strip()
        ]
        if query_candidates and db is not None:
            matched_reports = await db.scam_reports.find(
                {"indicator_value": {"$in": query_candidates}}
            ).to_list(length=5)
            if matched_reports:
                rep = matched_reports[0]
                results[RiskCategory.RECRUITER_VERIFICATION].risk_factors.append(
                    RiskFactor(
                        category=RiskCategory.RECRUITER_VERIFICATION,
                        severity=Severity.HIGH,
                        description="Matches confirmed scam indicator in community blacklist.",
                        evidence=(
                            f"Indicator '{rep['indicator_value']}' was previously reported by job seekers: "
                            f"'{rep['description']}'."
                        ),
                        source="community_scam_registry",
                        confidence=0.99,
                    )
                )
                results[RiskCategory.RECRUITER_VERIFICATION].score = max(
                    results[RiskCategory.RECRUITER_VERIFICATION].score, 90.0
                )
                results[RiskCategory.RECRUITER_VERIFICATION].analyzed = True
    except Exception as exc:
        logger.warning("Community scam lookup error: %s", exc)


    # ------------------------------------------------------------------
    # 3. Aggregate via risk engine
    # ------------------------------------------------------------------
    risk_score, band, rec, confidence, category_scores, risk_factors = score_assessment(results)


    # ------------------------------------------------------------------
    # 4. Determine Active Inputs List
    # ------------------------------------------------------------------
    active_inputs: list[str] = []
    if request.url and request.url.strip():
        active_inputs.append("Job URL")
    if request.description and request.description.strip():
        active_inputs.append("Job Description")
    if request.company_name and request.company_name.strip():
        active_inputs.append("Company Name")
    if (request.recruiter_email and request.recruiter_email.strip()) or (request.recruiter_name and request.recruiter_name.strip()) or (request.recruiter_phone and request.recruiter_phone.strip()):
        active_inputs.append("Recruiter Details")
    if request.message and request.message.strip():
        active_inputs.append("Email / Message")
    if document_bytes:
        active_inputs.append(f"Document ({document_filename or 'Uploaded File'})")

    # ------------------------------------------------------------------
    # 5. Build response and update the DB record
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
        active_inputs=active_inputs,
        created_at=now,
    )

    if db is not None:
        try:
            clean_email = request.user_email.strip().lower() if request.user_email else None
            update_coro = db.assessments.update_one(
                {"id": assessment_id},
                {"$set": {
                    "status": AssessmentStatus.COMPLETED.value,
                    "risk_score": risk_score,
                    "risk_band": band.value,
                    "recommendation": rec.value,
                    "confidence": confidence,
                    "category_scores": [cs.model_dump() for cs in category_scores],
                    "risk_factors": [rf.model_dump() for rf in risk_factors],
                    "active_inputs": active_inputs,
                    "updated_at": now.isoformat(),
                    "user_id": request.user_id,
                    "user_email": clean_email,
                }},
            )
            await asyncio.wait_for(update_coro, timeout=4.0)
            if clean_email:
                clean_company = request.company_name.strip() if request.company_name else "Hiring Entity"
                job_title = f"{clean_company} Opportunity"
                history_id = f"HS-{assessment_id[:8].upper()}"
                hist_item = {
                    "id": history_id,
                    "assessment_id": assessment_id,
                    "user_email": clean_email,
                    "user_id": request.user_id,
                    "jobTitle": job_title,
                    "title": job_title,
                    "company": clean_company,
                    "url": request.url or "",
                    "recruiterEmail": request.recruiter_email or "",
                    "recruiterName": request.recruiter_name or "",
                    "date": now.strftime("%Y-%m-%d"),
                    "scanDate": now.strftime("%b %d, %Y • %I:%M %p"),
                    "riskScore": round(risk_score),
                    "score": round(risk_score),
                    "riskLevel": "high" if band in (RiskBand.HIGH, RiskBand.VERY_HIGH) else "moderate" if band == RiskBand.MODERATE else "low",
                    "recommendation": rec.value,
                    "verdict": rec.value,
                    "type": "Job Listing",
                    "confidence": f"{round(confidence * 100)}%",
                    "summary": f"Risk score {round(risk_score)}/100 ({band.value}). Recommendation: {rec.value}.",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
                hist_coro = db.user_history.update_one(
                    {"id": history_id, "user_email": clean_email},
                    {"$set": hist_item},
                    upsert=True,
                )
                await asyncio.wait_for(hist_coro, timeout=4.0)
        except Exception as exc:
            logger.warning("Database update skipped or timed out for assessment %s: %s", assessment_id, exc)

    logger.info(
        "Assessment %s completed — score=%.1f band=%s rec=%s confidence=%.2f inputs=%s",
        assessment_id, risk_score, band.value, rec.value, confidence, active_inputs,
    )
    return response
