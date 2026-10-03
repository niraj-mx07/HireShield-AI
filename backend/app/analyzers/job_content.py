"""Job Content Analysis — category weight 20 %.

Classifies job-posting text for scam indicators using behavioural signals
rather than brand vocabulary, backed by a trained machine learning text
classifier (TF-IDF + Logistic Regression).

Classification policy (see :mod:`app.services.job_content_signals`):

* **Legal nouns and geographic indicators are neutral** — ``Pvt``, ``Ltd``,
  ``Inc``, ``Corp`` and ``India`` never contribute to the score.
* **Brand names are neutral** — mentioning ``Tata``, ``TCS``, ``Google`` or
  ``Amazon`` cannot raise risk on its own ("brand poisoning" defence).
* **Risk escalates only on explicit deceptive mechanics** — advance-fee
  demands, fake-check equipment loops, chat-only hiring channels, and grossly
  inflated compensation benchmarks.
* **Contextual override** — a standard corporate hiring structure combined with
  an explicit "no fee is charged" statement defaults the score to SAFE (<15).
"""

from __future__ import annotations

import logging

from app.models.schemas import (
    CategoryResult,
    RiskCategory,
    RiskFactor,
    Severity,
)
from app.services import job_content_signals
from app.services.model_loader import get_job_content_model

logger = logging.getLogger(__name__)

# Behavioural-signal scoring policy (see app/services/job_content_signals.py).
_BEHAVIORAL_HIGH_WEIGHT = 45.0    # each explicit high-severity mechanic
_BEHAVIORAL_MEDIUM_WEIGHT = 30.0  # each moderate mechanic
_BEHAVIORAL_HIGH_FLOOR = 65.0     # any explicit high-severity mechanic -> high band
_SAFE_OVERRIDE_CEILING = 12.0     # corporate process + explicit "no fee" -> SAFE (<15)


async def analyze(
    description: str | None = None,
    company_name: str | None = None,
    message: str | None = None,
    page_text: str | None = None,
    document_text: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Analyse job-posting content and recruiter messages for risk indicators using ML text classification.

    Args:
        description: Raw job description text.
        company_name: Name of the hiring company/organisation.
        message: Recruiter communication or task description.
        page_text: Visible text retrieved from the listing URL (when the user
            granted consent and the page was fetched via the web-retrieval
            service).
        document_text: Plain text extracted from an uploaded offer letter /
            job PDF.  Lets document-only submissions be classified too.

    Returns:
        A :class:`CategoryResult` with score (0–100), explainable risk factors,
        and ``analyzed=True`` when the model ran successfully, or
        ``analyzed=False`` if input was missing or model artifacts were unavailable.
    """
    # 1. Check if input text is available
    text_components = [
        p.strip()
        for p in (company_name, description, message, page_text, document_text)
        if p and p.strip()
    ]
    if not text_components:
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    combined_text = " ".join(text_components)

    # 2. Retrieve cached model artifacts
    vectorizer, model = get_job_content_model()
    if vectorizer is None or model is None:
        logger.warning(
            "Job content ML artifacts unavailable; skipping content classification."
        )
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    # 3. Neutralise legal nouns, geographic indicators and brand names, then
    #    vectorise and predict.  Masking happens BEFORE the vectoriser so those
    #    tokens resolve to out-of-vocabulary n-grams (zero weight).
    neutralized_text = job_content_signals.neutralize_text(combined_text)
    try:
        features = vectorizer.transform([neutralized_text])
        if hasattr(model, "predict_proba"):
            # Probabilities for [class 0 (legitimate), class 1 (fraudulent)]
            probabilities = model.predict_proba(features)[0]
            fraud_prob = float(probabilities[1])
        else:
            pred = model.predict(features)[0]
            fraud_prob = 1.0 if pred == 1 else 0.0

        # Neutralised ML probability, normalised to 0–100.
        ml_score = round(min(max(fraud_prob * 100.0, 0.0), 100.0), 2)
    except Exception as exc:
        logger.error("Error during job content model inference: %s", exc, exc_info=True)
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    # 4. Extract explainable top feature n-grams that triggered the model
    detected_phrases: list[str] = []
    try:
        if hasattr(model, "coef_") and hasattr(vectorizer, "get_feature_names_out"):
            feature_names = vectorizer.get_feature_names_out()
            row, cols = features.nonzero()
            word_weights = []
            for col_idx in cols:
                w = float(model.coef_[0][col_idx]) * float(features[0, col_idx])
                if w > 0.15:  # positive contribution toward fraud
                    word_weights.append((feature_names[col_idx], w))
            # Sort top positive contributing features
            word_weights.sort(key=lambda x: x[1], reverse=True)
            detected_phrases = [w[0] for w in word_weights[:5]]
    except Exception as e:
        logger.debug("Feature importance extraction skipped: %s", e)

    # 5. Behavioural signals + contextual override
    #    Risk escalates only on explicit deceptive mechanics.  Brand names and
    #    legal / geographic nouns never carry weight on their own.
    signals = job_content_signals.detect_behavioral_signals(combined_text)
    high_signals = [s for s in signals if s.severity is Severity.HIGH]
    medium_signals = [s for s in signals if s.severity is Severity.MEDIUM]

    corporate_structure = job_content_signals.has_corporate_structure(combined_text)
    explicit_no_fee = job_content_signals.has_explicit_no_fee(combined_text)
    safe_override = corporate_structure and explicit_no_fee and not high_signals

    behavioral_score = min(
        100.0,
        _BEHAVIORAL_HIGH_WEIGHT * len(high_signals)
        + _BEHAVIORAL_MEDIUM_WEIGHT * len(medium_signals),
    )

    phrases_snippet = (
        f" (Key signals: {', '.join(repr(p) for p in detected_phrases)})"
        if detected_phrases
        else ""
    )

    risk_factors: list[RiskFactor] = []

    if safe_override:
        # Contextual override: standard corporate process + explicit no-fee.
        score = round(min(ml_score, _SAFE_OVERRIDE_CEILING), 2)
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.JOB_CONTENT,
                severity=Severity.LOW,
                description=(
                    "Standard corporate hiring process with an explicit statement that "
                    "no recruitment fee is charged at any stage."
                ),
                evidence=(
                    "Structured hiring indicators (interview rounds, assessments, "
                    "background checks) are present and the listing states that no fee "
                    "is charged to applicants."
                ),
                source="contextual_no_fee_override",
                confidence=0.9,
            )
        )
    elif high_signals:
        # Explicit fraudulent mechanics always escalate the score.
        score = round(max(ml_score, behavioral_score, _BEHAVIORAL_HIGH_FLOOR), 2)
        risk_factors.extend(_signal_to_factor(s) for s in signals)
    elif medium_signals:
        score = round(max(ml_score, behavioral_score), 2)
        risk_factors.extend(_signal_to_factor(s) for s in medium_signals)
    else:
        # No explicit mechanics detected: fall back to the neutralised ML score.
        score = ml_score
        risk_factors.extend(_ml_risk_factors(score, fraud_prob, phrases_snippet))

    return CategoryResult(score=score, risk_factors=risk_factors, analyzed=True)


def _signal_to_factor(signal: job_content_signals.BehavioralSignal) -> RiskFactor:
    """Map a behavioural signal onto the public risk-factor schema."""
    return RiskFactor(
        category=RiskCategory.JOB_CONTENT,
        severity=signal.severity,
        description=signal.description,
        evidence=signal.evidence,
        source=signal.source,
        confidence=signal.confidence,
    )


def _ml_risk_factors(
    score: float, fraud_prob: float, phrases_snippet: str
) -> list[RiskFactor]:
    """Explainable fallback indicators derived from the neutralised ML score."""
    if score >= 70.0:
        return [
            RiskFactor(
                category=RiskCategory.JOB_CONTENT,
                severity=Severity.HIGH,
                description=(
                    "Text content exhibits strong similarity with patterns "
                    "characteristic of fraudulent or deceptive job listings."
                ),
                evidence=(
                    f"Statistical text classification model estimated high risk probability "
                    f"at {score:.1f}% based on linguistic and phrase patterns{phrases_snippet}."
                ),
                source="ml_job_content_classifier",
                confidence=round(fraud_prob, 2),
            )
        ]
    if score >= 35.0:
        return [
            RiskFactor(
                category=RiskCategory.JOB_CONTENT,
                severity=Severity.MEDIUM,
                description=(
                    "Text content exhibits moderate similarity with elevated-risk "
                    "or non-standard job listing patterns."
                ),
                evidence=(
                    f"Statistical text classification model estimated elevated risk "
                    f"probability at {score:.1f}%{phrases_snippet}."
                ),
                source="ml_job_content_classifier",
                confidence=round(fraud_prob, 2),
            )
        ]
    if score >= 20.0:
        return [
            RiskFactor(
                category=RiskCategory.JOB_CONTENT,
                severity=Severity.LOW,
                description=(
                    "Text content shows minor linguistic indicators sometimes "
                    "observed in lower-confidence postings."
                ),
                evidence=(
                    f"Statistical text classification model estimated low risk "
                    f"probability at {score:.1f}%."
                ),
                source="ml_job_content_classifier",
                confidence=round(1.0 - fraud_prob, 2),
            )
        ]
    return []
