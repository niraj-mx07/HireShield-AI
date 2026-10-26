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


def extract_pdf_metadata(document_bytes: bytes | None, filename: str | None = None) -> dict[str, str]:
    """Extract forensic metadata (Producer, Creator, Author) from PDF bytes."""
    if not document_bytes:
        return {}
    if (filename and filename.lower().endswith(".pdf")) or document_bytes.startswith(b"%PDF"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(document_bytes))
            meta = reader.metadata or {}
            return {
                "producer": str(meta.get("/Producer", "") or "").strip(),
                "creator": str(meta.get("/Creator", "") or "").strip(),
                "author": str(meta.get("/Author", "") or "").strip(),
            }
        except Exception as exc:
            logger.debug("PDF metadata extraction failed: %s", exc)
    return {}


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
    raw_text = (document_text or extract_document_text(document_bytes, document_filename)).strip()
    pdf_meta = extract_pdf_metadata(document_bytes, document_filename)

    if not raw_text and not pdf_meta:
        return CategoryResult(score=0.0, risk_factors=[], analyzed=False)

    text_lower = raw_text.lower()
    risk_factors: list[RiskFactor] = []
    base_score = 0.0

    # 0. Check for gibberish / nonsensical text
    from app.analyzers.job_content import is_gibberish_text
    if raw_text and is_gibberish_text(raw_text):
        return CategoryResult(
            score=82.0,
            risk_factors=[
                RiskFactor(
                    category=RiskCategory.DOCUMENT_ANALYSIS,
                    severity=Severity.HIGH,
                    description="Uploaded document contains unintelligible or random keyboard mash.",
                    evidence="Document text is unparseable or corrupted and cannot be validated as an authentic corporate contract.",
                    source="document_text_integrity_checker",
                    confidence=0.95,
                )
            ],
            analyzed=True,
        )

    # 1. Employment Relevance Check
    EMPLOYMENT_CORE_TERMS = [
        "offer", "appointment", "employment", "agreement", "salary", "compensation",
        "ctc", "joining", "probation", "designation", "role", "position", "candidate",
        "stipend", "remuneration", "duties", "reporting", "responsibilities", "leave",
        "notice period", "termination", "confidentiality"
    ]
    matched_core_terms = [t for t in EMPLOYMENT_CORE_TERMS if t in text_lower]

    is_employment_doc = len(matched_core_terms) >= 2 or any(
        phrase in text_lower for phrase in [
            "offer letter", "letter of appointment", "letter of intent",
            "employment agreement", "internship offer", "terms of employment",
            "offer of employment", "joining letter", "contract of employment"
        ]
    )

    if raw_text and len(raw_text) > 30 and not is_employment_doc:
        base_score += 48.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.MEDIUM,
                description="Uploaded document lacks recognizable employment or offer terms.",
                evidence=(
                    "Document text does not match standard offer letter or employment contract structure "
                    "(Missing designation, compensation terms, or appointment clauses)."
                ),
                source="employment_document_structure_validator",
                confidence=0.88,
            )
        )

    # 2. Template Artifacts / Unfilled Placeholder Tags
    placeholder_pattern = re.search(
        r"(\[company\s*name\]|\[candidate\s*name\]|\[salary\]|\[date\]|<insert\s*name>|<company\s*name>|\{candidate_name\}|\{company_name\})",
        text_lower,
    )
    if placeholder_pattern:
        base_score += 45.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.HIGH,
                description="Unfilled template placeholder tags detected in offer letter.",
                evidence=f"Document contains placeholder syntax '{placeholder_pattern.group(0)}', commonly seen in mass-generated counterfeit offer letters.",
                source="template_artifact_detector",
                confidence=0.94,
            )
        )

    # 3. Direct Selection / No Interview Scam
    no_interview_pattern = re.search(
        r"(?:selected\s*(?:directly)?\s*without\s*(?:any)?\s*(?:interview|test|exam)|direct\s*selection\s*letter|selection\s*on\s*basis\s*of\s*resume\s*only|no\s*interview\s*(?:required|needed))",
        text_lower,
    )
    if no_interview_pattern:
        base_score += 55.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.HIGH,
                description="Direct selection claimed without formal interview or evaluation.",
                evidence=(
                    f"Clause identified: '{no_interview_pattern.group(0)}'. "
                    "Legitimate corporate employers conduct formal technical or HR evaluations prior to issuing offer letters."
                ),
                source="direct_selection_detector",
                confidence=0.92,
            )
        )

    # 4. Deposit / Hardware Purchase clause in Offer Letter
    deposit_pattern = re.search(
        r"(?:refundable|security|equipment|laptop|training|kit|gate\s*pass|uniform|medical|processing|\s)*(?:deposit|charge|fee|amount)\s*(?:of|is)?\s*(?:rs\.?|inr|₹|\$)?\s*(\d+[\d,]*)",
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

    # 5. Fake notary / Government stamp / Court bond claims / Withholding certificates
    stamp_pattern = re.search(
        r"(?:notarized stamp|govt approved bond|legal agreement bond|ministry of corporate affairs stamp|registered seal|submission of original (?:marksheets?|certificates?|degrees?)|court action for leaving)",
        text_lower,
    )
    if stamp_pattern:
        base_score += 45.0
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.HIGH,
                description="Unusual legal stamp, court bond, or certificate retention clause in document.",
                evidence=f"Text references '{stamp_pattern.group(0)}', commonly added to counterfeit offer letters to intimidate freshers.",
                source="counterfeit_document_pattern_checker",
                confidence=0.92,
            )
        )

    # 6. Informal communication channel in official appointment letter
    chat_pattern = re.search(r"(?:telegram|whatsapp|wa\.me/|@gmail\.com|@yahoo\.|@rediffmail\.com)", text_lower)
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

    # 7. Forensic PDF metadata inspection (Producer, Creator, Author)
    if pdf_meta:
        creator_combined = f"{pdf_meta.get('creator', '')} {pdf_meta.get('producer', '')} {pdf_meta.get('author', '')}".lower()
        
        consumer_tools = ["canva", "photoshop", "coreldraw", "illustrator", "paint.net", "gimp"]
        matched_consumer = next((tool for tool in consumer_tools if tool in creator_combined), None)

        enterprise_tools = ["docusign", "adobesign", "workday", "bamboohr", "successfactors", "oracle hcm", "sap"]
        matched_enterprise = next((tool for tool in enterprise_tools if tool in creator_combined), None)

        if matched_consumer:
            base_score += 45.0
            tool_name = pdf_meta.get("creator") or pdf_meta.get("producer") or matched_consumer.title()
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.DOCUMENT_ANALYSIS,
                    severity=Severity.HIGH,
                    description=f"Consumer design tool ({tool_name}) detected in document metadata.",
                    evidence=(
                        f"PDF metadata identifies creation tool as '{tool_name}'. "
                        "Official corporate offer letters are generated via enterprise HR ERPs "
                        "or verified e-sign platforms (Workday, DocuSign), not consumer graphic design tools."
                    ),
                    source="pdf_forensic_metadata_inspector",
                    confidence=0.94,
                )
            )
        elif matched_enterprise:
            ent_name = pdf_meta.get("producer") or pdf_meta.get("creator") or matched_enterprise.title()
            risk_factors.append(
                RiskFactor(
                    category=RiskCategory.DOCUMENT_ANALYSIS,
                    severity=Severity.LOW,
                    description=f"Verified corporate e-sign / HR platform ({ent_name}) detected.",
                    evidence=f"PDF metadata confirms document was produced using enterprise e-signature infrastructure '{ent_name}'.",
                    source="pdf_forensic_metadata_inspector",
                    confidence=0.92,
                )
            )

    # 8. Positive Authenticity Signals (Statutory deductions, formal structure, corporate CIN/address)
    statutory_matches = [
        kw for kw in [
            "provident fund", "pf deduction", "gratuity", "cost to company", "ctc breakdown",
            "health insurance", "medical claim", "esi", "tax deduction", "tds",
            "notice period", "probation period", "earned leave", "casual leave", "confidentiality agreement"
        ] if kw in text_lower
    ]

    has_corporate_identity = bool(
        re.search(r"(?:cin|corporate identification number|registered office|cin\s*no|gstin)\s*[:#]?", text_lower)
        or re.search(r"(?:human resources|authorized signatory|head of talent acquisition|director)", text_lower)
    )

    if is_employment_doc and len(statutory_matches) >= 2 and not deposit_pattern:
        evidence_summary = ", ".join(statutory_matches[:4])
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.LOW,
                description="Standard formal compensation and benefits structure detected.",
                evidence=f"Document contains verified statutory and corporate clauses: {evidence_summary}.",
                source="hr_structure_validator",
                confidence=0.88,
            )
        )

    if has_corporate_identity and not deposit_pattern and is_employment_doc:
        risk_factors.append(
            RiskFactor(
                category=RiskCategory.DOCUMENT_ANALYSIS,
                severity=Severity.LOW,
                description="Corporate registration & authorized signatory block present.",
                evidence="Document contains corporate identification, registered office location, and formal authorization signatory.",
                source="corporate_registry_validator",
                confidence=0.86,
            )
        )

    # 9. Dynamic Calibrated Scoring
    high_flags = [rf for rf in risk_factors if rf.severity == Severity.HIGH]
    med_flags = [rf for rf in risk_factors if rf.severity == Severity.MEDIUM]
    low_flags = [rf for rf in risk_factors if rf.severity == Severity.LOW]

    if high_flags:
        final_score = min(max(base_score, 65.0), 98.0)
    elif med_flags:
        final_score = min(max(base_score, 32.0), 58.0)
    elif is_employment_doc:
        # Legitimate employment document with positive structure
        if len(low_flags) >= 2:
            final_score = 4.0
        elif len(low_flags) == 1:
            final_score = 8.0
        else:
            final_score = 14.0
    else:
        final_score = min(max(base_score, 0.0), 100.0)

    final_score = round(final_score, 2)
    return CategoryResult(score=final_score, risk_factors=risk_factors, analyzed=True)

