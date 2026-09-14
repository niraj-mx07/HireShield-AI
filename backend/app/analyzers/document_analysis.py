"""Document Analysis — category weight 10 %.

Reviews uploaded offer letters and PDFs for structural consistency,
formatting anomalies, payment clauses, and conflicts with verified
public information.

This module is currently a **stub** that returns a neutral score.
"""

from __future__ import annotations

from app.models.schemas import CategoryResult, RiskCategory


async def analyze(
    document_bytes: bytes | None = None,
    document_filename: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Analyse an uploaded document for risk indicators.

    Args:
        document_bytes: Raw bytes of the uploaded file.
        document_filename: Original filename (used for type detection).

    Returns:
        A :class:`CategoryResult` — stub returns neutral score.
    """
    # TODO: Implement document analysis
    #  - Offer letter structure validation
    #  - Payment clause detection
    #  - Logo / contact anomaly checks
    #  - Cross-reference with verified company info
    return CategoryResult(score=0.0, risk_factors=[], analyzed=False)
