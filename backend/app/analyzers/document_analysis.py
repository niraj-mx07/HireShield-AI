"""Document Analysis — category weight 10 %.

Extracts text from uploaded PDF or document offer letters using pypdf.
Reviews document structure, payment / deposit clauses, fake stamp annotations,
and non-standard HR onboarding procedures.
"""

from __future__ import annotations

import io
import logging
import re

from app.models.schemas import (
    CategoryResult,
    RiskCategory,
    RiskFactor,
    Severity,
)

logger = logging.getLogger(__name__)


def extract_document_text(document_bytes: bytes | None, filename: str | None = None) -> str:
    """Extract readable text from PDF bytes or raw text document."""
    if not document_bytes:
        return ""

    text = ""
    # Try pypdf extraction if PDF
    if filename and filename.lower().endswith(".pdf") or document_bytes.startswith(b"%PDF"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(document_bytes))
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text += f"\n{page_text}"
        except Exception as exc:
            logger.warning("pypdf extraction failed on %s: %s", filename, exc)

    # If text is still empty or wasn't a PDF, attempt utf-8 / latin-1 decoding
    if not text.strip():
        try:
            text = document_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = document_bytes.decode("latin-1", errors="ignore")

    return text.strip()


async def analyze(
    document_bytes: bytes | None = None,
    document_filename: str | None = None,
    document_text: str | None = None,
    **kwargs,
) -> CategoryResult:
    """Analyse uploaded offer letter or PDF document.

    Returns:
        A :class:`CategoryResult` with score (0–100), risk factors, and analyzed=True/False.
    """
    raw_text = document_text or extract_document_text(document_bytes, document_filename)
    if not raw_text.strip():
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    text_lower = raw_text.lower()
    risk_factors: list[RiskFactor] = []
    base_score = 0.0

    # 1. Deposit / Hardware Purchase clause in Offer Letter
    deposit_pattern = re.search(
        r"(?:refundable|security|equipment|laptop|training|kit|\s)*(?:deposit|charge|fee|amount)\s*(?:of|is)?\s*(?:rs\.?|inr|₹|\$)?\s*(\d+[\d,]*)",
        text_lower,
    )
    if deposit_pattern:
        base_score += 65.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.HIGH,
                description="Security deposit or equipment purchase clause in offer letter.",
                evidence=(
                    f"Offer letter specifies financial condition: '{deposit_pattern.group(0)}'. "
                    "Legitimate corporate offer letters do not require candidates to pay fees or purchase gear."
                ),
                source="pdf_clause_extractor",
                confidence=0.96,
            )
        )

    # 2. Fake notary / Government stamp claims in private employment contract
    stamp_pattern = re.search(
        r"(?:notarized stamp|govt approved bond|legal agreement bond|ministry of corporate affairs stamp|registered seal)",
        text_lower,
    )
    if stamp_pattern:
        base_score += 35.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.MEDIUM,
                description="Unusual legal stamp or court bond phrasing in offer document.",
                evidence=f"Text references '{stamp_pattern.group(0)}', commonly added to counterfeit offer letters to intimidate freshers.",
                source="counterfeit_document_pattern_checker",
                confidence=0.88,
            )
        )

    # 3. Informal communication channel in official appointment letter
    chat_pattern = re.search(r"(?:telegram|whatsapp|wa\.me/|@gmail\.com|@yahoo\.)", text_lower)
    if chat_pattern:
        base_score += 35.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.MEDIUM,
                description="Offer document directs candidate to informal chat channel or personal email.",
                evidence=f"Document references contact '{chat_pattern.group(0)}' for onboarding and reporting.",
                source="document_channel_inspector",
                confidence=0.90,
            )
        )

    # 4. If document contains legitimate employment terms (provident fund, CTC, gratuity, medical)
    has_legit_clauses = any(
        kw in text_lower for kw in ["provident fund", "pf", "gratuity", "cost to company", "ctc", "leaves", "health insurance"]
    )
    if has_legit_clauses and not deposit_pattern:
        base_score = max(base_score - 10.0, 5.0)
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.LOW,
                description="Standard formal compensation and benefits structure detected.",
                evidence="Document contains standard corporate employment clauses (PF, benefits, leave policy).",
                source="hr_structure_validator",
                confidence=0.85,
            )
        )

    final_score = round(min(max(base_score, 0.0), 100.0), 2)
    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)
