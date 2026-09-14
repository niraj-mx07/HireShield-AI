"""Job Content Analysis — category weight 20 %.

Evaluates job-posting text using a trained machine learning text classifier
(TF-IDF + Logistic Regression trained on validated job posting datasets).

Flags linguistic patterns, urgency, and anomalies characteristic of
fraudulent listings, mapping predicted probabilities into risk indicators
and confidence scores without asserting fraud as fact.
"""

from __future__ import annotations

import logging

from app.models.schemas import (
    CategoryResult,
    RiskCategory,
    RiskFactor,
    Severity,
)
from app.services.model_loader import get_job_content_model

logger = logging.getLogger(__name__)


async def analyze(
    description: str | None = None,
    company_name: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Analyse job-posting content for risk indicators using ML text classification.

    Args:
        description: Raw job description text.
        company_name: Name of the hiring company/organisation.

    Returns:
        A :class:`CategoryResult` with score (0–100), explainable risk factors,
        and ``analyzed=True`` when the model ran successfully, or
        ``analyzed=False`` if input was missing or model artifacts were unavailable.
    """
    # 1. Check if input text is available
    text_components = [p.strip() for p in (company_name, description) if p and p.strip()]
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

    # 3. Vectorise and predict fraud probability
    try:
        features = vectorizer.transform([combined_text])
        if hasattr(model, "predict_proba"):
            # Probabilities for [class 0 (legitimate), class 1 (fraudulent)]
            probabilities = model.predict_proba(features)[0]
            fraud_prob = float(probabilities[1])
        else:
            pred = model.predict(features)[0]
            fraud_prob = 1.0 if pred == 1 else 0.0

        # Normalise to 0–100 risk score
        score = round(min(max(fraud_prob * 100.0, 0.0), 100.0), 2)
    except Exception as exc:
        logger.error("Error during job content model inference: %s", exc, exc_info=True)
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    # 4. Construct explainable risk indicators based on risk score
    risk_factors: list[RiskFactor] = []

    if score >= 70.0:
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.JOB_CONTENT,
                severity=Severity.HIGH,
                description=(
                    "Text content exhibits strong similarity with patterns "
                    "characteristic of fraudulent or deceptive job listings."
                ),
                evidence=(
                    f"Statistical text classification model estimated risk probability "
                    f"at {score:.1f}% based on linguistic and phrase patterns."
                ),
                source="ml_job_content_classifier",
                confidence=round(fraud_prob, 2),
            )
        )
    elif score >= 35.0:
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.JOB_CONTENT,
                severity=Severity.MEDIUM,
                description=(
                    "Text content exhibits moderate similarity with elevated-risk "
                    "or non-standard job listing patterns."
                ),
                evidence=(
                    f"Statistical text classification model estimated elevated risk "
                    f"probability at {score:.1f}%."
                ),
                source="ml_job_content_classifier",
                confidence=round(fraud_prob, 2),
            )
        )
    elif score >= 20.0:
        risk_factors.append(
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
        )

    return CategoryResult(score=score, risk_factors=risk_factors, analyzed=True)
