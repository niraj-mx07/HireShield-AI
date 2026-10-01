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
    ExtractedEntity,
    RiskCategory,
    RiskFactor,
    Severity,
)
from app.services import nlp_entities, web_retrieval
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
    record = AssessmentRecord(id=assessment_id, input_summary=input_summary)
    await db.assessments.insert_one(record.model_dump())

    # ------------------------------------------------------------------
    # 2. Extract Document Text (if any) and Run All Analyzers
    # ------------------------------------------------------------------
    from app.analyzers.document_analysis import extract_document_text
    extracted_doc_text = extract_document_text(document_bytes, document_filename)

    # Retrieve the public listing page once, when the user consented and
    # retrieval is enabled.  The parsed page is shared by the job-content
    # analyzer (page text) and the company-verification analyzer (live checks).
    page = None
    page_attempted = False
    if consent and web_retrieval.is_enabled() and request.url and request.url.strip():
        page_attempted = True
        try:
            page = await web_retrieval.fetch_page(request.url)
        except Exception as exc:  # defensive — fetch_page never raises
            logger.warning("Web retrieval raised unexpectedly: %s", exc)
            page = None
    page_text = page.text if (page and page.text) else None

    results: dict[RiskCategory, CategoryResult] = {}

    results[RiskCategory.JOB_CONTENT] = await job_content.analyze(
        description=request.description,
        company_name=request.company_name,
        message=request.message,
        page_text=page_text,
    )
    results[RiskCategory.COMPANY_VERIFICATION] = await company_verification.analyze(
        company_name=request.company_name,
        url=request.url,
        consent=consent,
        page_extraction=page,
        page_attempted=page_attempted,
    )
    results[RiskCategory.RECRUITER_VERIFICATION] = await recruiter_verification.analyze(
        recruiter_email=request.recruiter_email,
        recruiter_name=request.recruiter_name,
        recruiter_phone=request.recruiter_phone,
        company_name=request.company_name,
        message=request.message,
        consent=consent,
    )
    results[RiskCategory.URL_WEBSITE] = await url_analysis.analyze(
        url=request.url,
        company_name=request.company_name,
        consent=consent,
    )
    results[RiskCategory.FINANCIAL_SCAM] = await financial_signals.analyze(
        description=request.description,
        message=request.message,
        document_text=extracted_doc_text,
    )
    results[RiskCategory.DOCUMENT_ANALYSIS] = await document_analysis.analyze(
        document_bytes=document_bytes,
        document_filename=document_filename,
        document_text=extracted_doc_text,
    )
    results[RiskCategory.INFORMATION_CONSISTENCY] = await consistency_check.analyze(
        description=request.description,
        url=request.url,
        company_name=request.company_name,
        recruiter_email=request.recruiter_email,
        message=request.message,
        document_text=extracted_doc_text,
    )

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
        if query_candidates:
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
    # 2c. Named-entity extraction (structured identifiers + NLP NER)
    # ------------------------------------------------------------------
    entities: list[ExtractedEntity] = []
    try:
        ner_input = "\n".join(
            part.strip()
            for part in (
                request.description,
                request.message,
                extracted_doc_text,
                page_text,
            )
            if part and part.strip()
        )
        extraction = nlp_entities.extract_entities(ner_input)
        entities = [
            ExtractedEntity(
                text=entity.text,
                label=entity.label,
                source=entity.source,
                confidence=entity.confidence,
            )
            for entity in extraction.entities
        ]
        logger.info(
            "Assessment %s — extracted %d entities (provider=%s)",
            assessment_id, len(entities), extraction.provider,
        )
    except Exception as exc:  # defensive — extract_entities never raises
        logger.warning("Entity extraction error: %s", exc)
        entities = []


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
        entities=entities,
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
            "active_inputs": active_inputs,
            "updated_at": now.isoformat(),
        }},
    )

    logger.info(
        "Assessment %s completed — score=%.1f band=%s rec=%s confidence=%.2f inputs=%s",
        assessment_id, risk_score, band.value, rec.value, confidence, active_inputs,
    )
    return response
