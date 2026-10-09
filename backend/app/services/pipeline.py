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
    CHAT_REDIRECT_GATE_SOURCE,
    ExtractedEntity,
    RiskCategory,
    RiskFactor,
    Severity,
    normalize_text_payloads,
)
from app.services import document_mining, message_threats, nlp_entities, web_retrieval
from app.services.job_metadata import extract_job_metadata
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

    # ------------------------------------------------------------------
    # 0. Fold alias text payloads into the analyzers' primary variables
    # ------------------------------------------------------------------
    # ``chat_transcript`` / ``message_log`` are accepted input keys; when the
    # canonical field is empty they become the payload the text engine analyses.
    # This runs before document mining so a user-pasted transcript is never
    # overridden by a document-derived description.
    folded_aliases = normalize_text_payloads(request)
    if folded_aliases:
        logger.info(
            "Assessment %s — alias input(s) folded into primary payloads: %s",
            assessment_id, ", ".join(folded_aliases),
        )

    # ------------------------------------------------------------------
    # Extract document text and mine inputs the user left blank
    # ------------------------------------------------------------------
    # This runs before the input summary, the DB record, the retrieval step
    # and the analyzers so everything downstream sees the same (possibly
    # document-enriched) inputs: offer letters routinely repeat the company
    # name, listing URL and recruiter contacts the user did not retype.
    from app.analyzers.document_analysis import extract_document_text
    extracted_doc_text = extract_document_text(document_bytes, document_filename)
    document_derived_inputs = document_mining.fill_missing_fields(
        request, extracted_doc_text
    )
    if document_derived_inputs:
        logger.info(
            "Assessment %s — inputs derived from document: %s",
            assessment_id, ", ".join(document_derived_inputs),
        )

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
            chat_transcript=request.chat_transcript,
            message_log=request.message_log,
            has_document=document_bytes is not None,
        ))),
    )

    # ------------------------------------------------------------------
    # 1. Create a pending record in the database (best-effort)
    # ------------------------------------------------------------------
    # Persistence must never fail an assessment: when MongoDB is down,
    # mis-configured, or unreachable the scan still runs and returns a
    # full report — only history/blacklist lookups are skipped.
    db = None
    try:
        db = get_database()
    except Exception as exc:
        logger.warning(
            "Assessment %s — database unavailable at startup, running without persistence: %s",
            assessment_id, exc,
        )
    input_summary = build_input_summary(
        url=request.url,
        description=request.description,
        company_name=request.company_name,
        recruiter_email=request.recruiter_email,
        recruiter_name=request.recruiter_name,
        recruiter_phone=request.recruiter_phone,
        message=request.message,
        chat_transcript=request.chat_transcript,
        message_log=request.message_log,
        has_document=document_bytes is not None,
    )
    if db is not None:
        try:
            record = AssessmentRecord(id=assessment_id, input_summary=input_summary)
            await db.assessments.insert_one(record.model_dump())
        except Exception as exc:
            logger.warning(
                "Assessment %s — pending-record write skipped (DB unavailable): %s",
                assessment_id, exc,
            )
            db = None

    # ------------------------------------------------------------------
    # 2. Run All Analyzers (document text was extracted above)
    # ------------------------------------------------------------------
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
    # Only use retrieved page text for content classification if the request succeeded (< 400)
    # and has verifiable job posting markers (avoids feeding 404 error page text into ML classifier)
    page_text = (
        page.text
        if (page and page.text and getattr(page, "status_code", 0) and page.status_code < 400 and page.has_job_posting)
        else None
    )

    results: dict[RiskCategory, CategoryResult] = {}

    results[RiskCategory.JOB_CONTENT] = await job_content.analyze(
        description=request.description,
        company_name=request.company_name,
        message=request.message,
        page_text=page_text,
        document_text=extracted_doc_text,
        page_attempted=page_attempted,
        page_extraction=page,
        url=request.url,
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
        page_extraction=page,
        page_attempted=page_attempted,
    )
    results[RiskCategory.FINANCIAL_SCAM] = await financial_signals.analyze(
        description=request.description,
        message=request.message,
        document_text=extracted_doc_text,
        chat_transcript=request.chat_transcript,
        message_log=request.message_log,
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
    # 2b. Cross-reference community scam blacklist (skipped when DB is down)
    # ------------------------------------------------------------------
    try:
        query_candidates = [
            v.strip().lower() for v in (
                request.recruiter_email,
                request.recruiter_phone,
                request.url,
            ) if v and v.strip()
        ]
        if db is not None and query_candidates:
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
    # 2c. Message & Transcript Analysis Engine — zero-tolerance
    #     chat-redirection gate (Rules 1 & 3)
    # ------------------------------------------------------------------
    # Every conversational payload field is scanned together so a transcript
    # pasted under any key still reaches the gate.  A hit emits the
    # CHAT_REDIRECT_GATE_SOURCE sentinel, which floors the overall score at
    # 92+ and forces DON'T APPLY in the risk engine.  Legitimate Microsoft
    # Teams / Zoom / Webex interviews with a corporate invitation domain
    # bypass the gate entirely.
    try:
        transcript_payload = "\n".join(
            part.strip()
            for part in (
                request.description,
                request.message,
                request.chat_transcript,
                request.message_log,
            )
            if part and part.strip()
        )
        redirection_hit = message_threats.detect_chat_redirection(transcript_payload)
        if redirection_hit is not None:
            recruiter_result = results[RiskCategory.RECRUITER_VERIFICATION]
            recruiter_result.risk_factors.append(
                RiskFactor(
                    category=RiskCategory.RECRUITER_VERIFICATION,
                    severity=Severity.HIGH,
                    description=(
                        "Hiring communication redirected to a personal or anonymous "
                        "chat network."
                    ),
                    evidence=(
                        f"Platform '{redirection_hit.platform}' referenced as the channel "
                        f"for an interview or onboarding briefing. Evidence: "
                        f"{redirection_hit.evidence} Legitimate employers conduct "
                        "hiring over official corporate channels."
                    ),
                    source=CHAT_REDIRECT_GATE_SOURCE,
                    confidence=0.97,
                )
            )
            recruiter_result.score = max(recruiter_result.score, 92.0)
            recruiter_result.analyzed = True
            logger.info(
                "Assessment %s — chat-redirection gate raised (platform=%s)",
                assessment_id, redirection_hit.platform,
            )
    except Exception as exc:
        logger.warning("Chat-redirection gate error: %s", exc)


    # ------------------------------------------------------------------
    # 2d. Named-entity extraction (structured identifiers + NLP NER)
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
        # A body that arrived via ``chat_transcript`` is reported under its
        # real name rather than being mislabelled as a job description.
        active_inputs.append(
            "Chat Transcript" if "chat_transcript" in folded_aliases else "Job Description"
        )
    if (
        request.chat_transcript
        and request.chat_transcript.strip()
        and "chat_transcript" not in folded_aliases
    ):
        active_inputs.append("Chat Transcript")
    if request.company_name and request.company_name.strip():
        active_inputs.append("Company Name")
    if (request.recruiter_email and request.recruiter_email.strip()) or (request.recruiter_name and request.recruiter_name.strip()) or (request.recruiter_phone and request.recruiter_phone.strip()):
        active_inputs.append("Recruiter Details")
    if request.message and request.message.strip():
        active_inputs.append("Email / Message")
    if (
        request.message_log
        and request.message_log.strip()
        and "message_log" not in folded_aliases
    ):
        active_inputs.append("Message Log")
    if document_bytes:
        active_inputs.append(f"Document ({document_filename or 'Uploaded File'})")

    # ------------------------------------------------------------------
    # 5. Extract Key Job Parameters & Build Response
    # ------------------------------------------------------------------
    job_meta = extract_job_metadata(
        request=request,
        document_text=extracted_doc_text,
        document_filename=document_filename,
        page_text=page_text,
    )

    now = datetime.now(timezone.utc)
    response = AssessmentResponse(
        id=assessment_id,
        status=AssessmentStatus.COMPLETED,
        risk_score=risk_score,
        risk_band=band,
        recommendation=rec,
        confidence=confidence,
        company_name=job_meta.company_name,
        job_title=job_meta.job_title,
        recruiter_name=job_meta.recruiter_name,
        recruiter_contact=job_meta.recruiter_contact,
        recruiter_email=job_meta.recruiter_email,
        recruiter_phone=job_meta.recruiter_phone,
        recruiter_linkedin=job_meta.recruiter_linkedin,
        detected_sources=job_meta.detected_sources,
        category_scores=category_scores,
        risk_factors=risk_factors,
        active_inputs=active_inputs,
        document_derived_inputs=document_derived_inputs,
        entities=entities,
        created_at=now,
    )

    if db is not None:
        try:
            await db.assessments.update_one(
                {"id": assessment_id},
                {"$set": {
                    "status": AssessmentStatus.COMPLETED.value,
                    "risk_score": risk_score,
                    "risk_band": band.value,
                    "recommendation": rec.value,
                    "confidence": confidence,
                    "detected_sources": job_meta.detected_sources,
                    "category_scores": [cs.model_dump() for cs in category_scores],
                    "risk_factors": [rf.model_dump() for rf in risk_factors],
                    "active_inputs": active_inputs,
                    "document_derived_inputs": document_derived_inputs,
                    "updated_at": now.isoformat(),
                }},
            )
        except Exception as exc:
            logger.warning(
                "Assessment %s — completion write skipped (DB unavailable): %s",
                assessment_id, exc,
            )

    logger.info(
        "Assessment %s completed — score=%.1f band=%s rec=%s company='%s' title='%s' sources=%s",
        assessment_id, risk_score, band.value, rec.value, job_meta.company_name, job_meta.job_title, job_meta.detected_sources,
    )
    return response
