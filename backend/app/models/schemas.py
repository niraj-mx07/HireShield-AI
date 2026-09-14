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

    At least one of ``url``, ``description``, ``company_name``, or a document
    upload (handled via multipart) must be provided.
    """
    url: Optional[str] = Field(None, description="Job/internship listing URL")
    description: Optional[str] = Field(None, description="Pasted job description text")
    company_name: Optional[str] = Field(None, description="Company or organisation name")
    recruiter_email: Optional[str] = Field(None, description="Recruiter email address")
    recruiter_name: Optional[str] = Field(None, description="Recruiter name")
    consent_for_external_lookups: bool = Field(
        False,
        description=(
            "Explicit user consent to perform external lookups "
            "(company verification, domain checks) that may transmit "
            "submitted content to third-party services."
        ),
    )


# ---------------------------------------------------------------------------
# Intermediate / analysis result schemas
# ---------------------------------------------------------------------------

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
    category_scores: List[CategoryScore] = Field(default_factory=list)
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


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
    risk_score: Optional[float] = None
    risk_band: Optional[RiskBand] = None
    recommendation: Optional[Recommendation] = None
    confidence: Optional[float] = None
    category_scores: List[CategoryScore] = Field(default_factory=list)
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
