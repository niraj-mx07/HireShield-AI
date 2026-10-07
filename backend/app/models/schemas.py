"""Pydantic v2 schemas for request/response validation and DB documents.

Design notes
------------
* All public-facing language uses *risk indicators* and *confidence levels*,
  never unqualified fraud claims (per README §Privacy and Safety Design).
* ``AssessmentRequest.consent_for_external_lookups`` must be ``True`` before
  the pipeline performs any external verification that sends user-submitted
  content to third-party services.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Risk-factor severity level."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskBand(str, Enum):
    """Risk band derived from the 0-100 score."""
    LOW = "low"              # 0–30
    MODERATE = "moderate"    # 31–60
    HIGH = "high"            # 61–80
    VERY_HIGH = "very_high"  # 81–100


class Recommendation(str, Enum):
    """Action recommendation for the user."""
    APPLY = "APPLY"
    HOLD = "HOLD"
    DONT_APPLY = "DON'T APPLY"


class AssessmentStatus(str, Enum):
    """Processing status of an assessment."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskCategory(str, Enum):
    """The seven risk-scoring categories and their canonical keys."""
    JOB_CONTENT = "job_content"
    COMPANY_VERIFICATION = "company_verification"
    RECRUITER_VERIFICATION = "recruiter_verification"
    URL_WEBSITE = "url_website"
    FINANCIAL_SCAM = "financial_scam"
    DOCUMENT_ANALYSIS = "document_analysis"
    INFORMATION_CONSISTENCY = "information_consistency"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class AssessmentRequest(BaseModel):
    """Input payload for creating a new assessment.

    At least one of ``url``, ``description``, ``company_name``, ``recruiter_email``,
    ``recruiter_name``, ``recruiter_phone``, ``message``, ``chat_transcript``,
    ``message_log``, or a document upload (handled via multipart) must be provided.
    """
    url: Optional[str] = Field(None, description="Job/internship listing URL")
    description: Optional[str] = Field(None, description="Pasted job description text")
    company_name: Optional[str] = Field(None, description="Company or organisation name")
    recruiter_email: Optional[str] = Field(None, description="Recruiter email address")
    recruiter_name: Optional[str] = Field(None, description="Recruiter name")
    recruiter_phone: Optional[str] = Field(None, description="Recruiter phone number or WhatsApp handle")
    message: Optional[str] = Field(None, description="Recruiter email body, WhatsApp, or Telegram message")
    chat_transcript: Optional[str] = Field(
        None,
        description="Pasted chat transcript (WhatsApp, Telegram, in-app chat)",
    )
    message_log: Optional[str] = Field(
        None,
        description="Pasted message log or email thread history",
    )
    consent_for_external_lookups: bool = Field(
        False,
        description=(
            "Explicit user consent to perform external lookups "
            "(company verification, domain checks) that may transmit "
            "submitted content to third-party services."
        ),
    )


def _has_text(value: Optional[str]) -> bool:
    """True when *value* carries non-whitespace content."""
    return bool(value and value.strip())


def normalize_text_payloads(request: AssessmentRequest) -> list[str]:
    """Fold the alias text fields into the pipeline's primary payload variables.

    The analyzers consume two text payloads: :attr:`AssessmentRequest.description`
    (the job/content body) and :attr:`AssessmentRequest.message` (the recruiter
    correspondence).  Callers may instead submit ``chat_transcript`` or
    ``message_log``.  When an alias is supplied and its canonical field is
    empty, the alias is copied across so the text processing engine analyses it
    instead of silently dropping it.  A canonical value the caller actually
    typed is never overwritten.

    Returns:
        The alias names that were folded in, e.g. ``["chat_transcript"]``.
    """
    folded: list[str] = []

    if not _has_text(request.description) and _has_text(request.chat_transcript):
        request.description = request.chat_transcript.strip()
        folded.append("chat_transcript")

    if not _has_text(request.message) and _has_text(request.message_log):
        request.message = request.message_log.strip()
        folded.append("message_log")

    return folded


# ---------------------------------------------------------------------------
# Intermediate / analysis result schemas
# ---------------------------------------------------------------------------

# Sentinel ``RiskFactor.source`` value marking an absolute, positively confirmed
# infrastructure failure — e.g. a recruiter domain that authoritatively returned
# zero MX records and therefore cannot send or receive mail at all.  The risk
# engine treats this as disqualifying and forces DON'T APPLY; it must never be
# softened into a HOLD.
CRITICAL_INFRA_FAILURE_SOURCE = "critical_infrastructure_failure"

# Sentinel ``RiskFactor.source`` value marking a confirmed zero-tolerance
# chat-redirection violation: an interview or onboarding briefing was moved
# onto a personal / anonymous chat network (Telegram, Signal, WhatsApp, bare
# ``@handle`` …) and no legitimate enterprise-video bypass applied.  The risk
# engine treats this as a hard gate — the overall score is floored at 92.0 and
# the verdict is forced to DON'T APPLY.  It can never be averaged down.
CHAT_REDIRECT_GATE_SOURCE = "chat_redirection_gate"

# Minimum overall risk score enforced while ``CHAT_REDIRECT_GATE_SOURCE`` is
# present among the aggregated risk factors.
CHAT_REDIRECT_GATE_SCORE_FLOOR = 92.0


class RiskFactor(BaseModel):
    """A single risk indicator surfaced by an analyzer."""
    category: RiskCategory
    severity: Severity
    description: str = Field(..., description="Human-readable risk indicator (never assert fraud)")
    evidence: str = Field("", description="Supporting evidence or observation")
    source: str = Field("", description="Origin of the evidence (e.g. 'domain_check', 'nlp_model')")
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence level for this indicator (0.0–1.0)",
    )


class CategoryScore(BaseModel):
    """Score breakdown for a single risk category."""
    category: RiskCategory
    score: float = Field(0.0, ge=0.0, le=100.0, description="Raw category score (0–100)")
    weight: float = Field(..., ge=0.0, le=1.0, description="Category weight in final score")
    weighted_score: float = Field(0.0, ge=0.0, description="score × weight contribution")
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    analyzed: bool = Field(False, description="Whether real analysis was performed vs. stub")


class CategoryResult(BaseModel):
    """Return type for individual analyzer modules."""
    score: float = Field(0.0, ge=0.0, le=100.0)
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    analyzed: bool = Field(False, description="True when real analysis ran, False for stubs")


class ExtractedEntity(BaseModel):
    """A named entity extracted from submitted or retrieved text.

    Entities are returned to the submitting user only and are **never**
    persisted to the database, so raw PII (emails, phone numbers) is not
    stored at rest.
    """
    text: str = Field(..., description="Surface form of the entity")
    label: str = Field(..., description="Entity label, e.g. EMAIL, PERSON, ORG")
    source: str = Field("", description="Extractor that produced it: regex, spacy, or transformers")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence (0.0–1.0)")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AssessmentResponse(BaseModel):
    """Full assessment report returned to the client."""
    id: str = Field(..., description="Assessment identifier")
    status: AssessmentStatus = AssessmentStatus.COMPLETED
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Overall risk score (0–100)")
    risk_band: RiskBand
    recommendation: Recommendation
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence based on evidence coverage",
    )
    company_name: str = Field("Unspecified Company", description="Parsed company or hiring organization")
    job_title: str = Field("Job Opportunity", description="Parsed job title or role")
    recruiter_name: Optional[str] = Field(None, description="Extracted recruiter name")
    recruiter_contact: Optional[str] = Field(None, description="Extracted recruiter contact info")
    recruiter_email: Optional[str] = Field(None, description="Extracted recruiter email")
    recruiter_phone: Optional[str] = Field(None, description="Extracted recruiter phone")
    recruiter_linkedin: Optional[str] = Field(None, description="Extracted recruiter LinkedIn URL")
    detected_sources: List[str] = Field(
        default_factory=list,
        description="List of detected input sources scanned for this assessment",
    )
    category_scores: List[CategoryScore] = Field(default_factory=list)
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    active_inputs: List[str] = Field(default_factory=list, description="Inputs supplied by the user")
    document_derived_inputs: List[str] = Field(
        default_factory=list,
        description=(
            "Request fields auto-filled from the uploaded document "
            "(field names only — values are never persisted)"
        ),
    )
    entities: List[ExtractedEntity] = Field(
        default_factory=list,
        description="Named entities extracted from the submitted / retrieved text (not persisted)",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database document model
# ---------------------------------------------------------------------------

class AssessmentRecord(BaseModel):
    """MongoDB document representation for a stored assessment.

    Raw PII is *not* persisted — only hashed identifiers and the structured
    analysis output.  The ``input_summary`` captures non-sensitive metadata
    about what was submitted (e.g. "url provided", "description provided").
    """
    id: str
    status: AssessmentStatus = AssessmentStatus.PENDING
    input_summary: dict = Field(
        default_factory=dict,
        description="Non-PII summary of submitted inputs (keys provided, lengths, etc.)",
    )
    detected_sources: List[str] = Field(default_factory=list)
    risk_score: Optional[float] = None
    risk_band: Optional[RiskBand] = None
    recommendation: Optional[Recommendation] = None
    confidence: Optional[float] = None
    category_scores: List[CategoryScore] = Field(default_factory=list)
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    active_inputs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Community Scam Registry Models
# ---------------------------------------------------------------------------

class ScamReportRequest(BaseModel):
    """Payload for submitting a community scam report."""
    indicator_type: str = Field(..., description="Type of indicator: upi_id, phone, email, telegram, domain")
    indicator_value: str = Field(..., description="The value: e.g. hrfee@okaxis, +919876543210, @task_earn")
    company_impersonated: Optional[str] = Field(None, description="Company the scammer pretended to represent")
    description: str = Field(..., description="Detailed explanation of the fraudulent recruitment attempt")
    loss_amount: Optional[float] = Field(None, ge=0.0, description="Amount lost or requested, if any")


class ScamReportResponse(BaseModel):
    """Response payload for a community scam report."""
    id: str
    indicator_type: str
    indicator_value: str
    company_impersonated: Optional[str] = None
    description: str
    loss_amount: Optional[float] = None
    reported_at: datetime

