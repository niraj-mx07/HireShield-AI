"""Mine structured fields from an uploaded document.

Offer letters and job PDFs routinely repeat information the user could have
skipped past: the hiring company's name, the listing URL, and recruiter
contact details.  Copying those values into *empty* request fields lets
analyzers that would otherwise be skipped (``company_verification``,
``url_website``, ``recruiter_verification``) run on real evidence, which
raises the assessment's evidence-coverage ``confidence`` without inventing
data.

Design rules:

* **Never override user input** — only fields the user left blank are filled
  (``fill_missing_fields``).
* **Conservative extraction** — deterministic label patterns first
  (``Company: Acme Ltd``), contextual ``ORG`` spans as a fallback; anything
  implausible is left alone rather than guessed.
* **Transparent** — every auto-filled field *name* is reported on the
  response as ``document_derived_inputs`` so the UI can show provenance and
  the user can correct it.  Field *values* are never persisted.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from app.models.schemas import AssessmentRequest
from app.services import nlp_entities
from app.services.nlp_entities import Entity

logger = logging.getLogger(__name__)

# Request fields that may be derived from document text.  Free-text fields
# (description, message) and personal names are deliberately excluded: they
# cannot be identified reliably enough to auto-fill.
DERIVABLE_FIELDS = ("url", "company_name", "recruiter_email", "recruiter_phone")

# "Company: Acme Pvt Ltd" / "Company Name - Acme" style labels.  Markdown or
# list prefixes ("**Company:**", "- Organisation:") are tolerated.
_COMPANY_LABEL_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*#>]+[ \t]*)*"
    r"(?:about\s+(?:the\s+)?|name\s+of\s+(?:the\s+)?)?"
    r"(?:company(?:[ \t]+name)?|organisation|organization|employer|firm)"
    r"[ \t]*(?::|-|–|—)"
    r"[ \t]*(?P<value>[^\r\n]+?)\s*$"
)

# Word-processor tables put the label and its value on *separate* lines
# ("Company" / "Acme Corp"), which is how every .docx offer letter lays out
# its details table.  This second pattern handles that shape.
_COMPANY_LABEL_NEXT_LINE_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*#>]+[ \t]*)*"
    r"(?:company(?:[ \t]+name)?|organisation|organization|employer|firm)"
    r"[ \t]*:?[ \t]*\r?\n"
    r"[ \t]*(?P<value>[^\r\n]+?)[ \t]*$"
)

# When the labelled value runs into prose ("Company: Acme Ltd is pleased to
# offer..."), cut at the start of the sentence tail.
_VALUE_CUT_RE = re.compile(
    r"\s+(?:is|are|was|were|has|have|had|offers?|presents?|hereby|will|pleased|"
    r"looking\s+for)\b.*",
    re.IGNORECASE | re.DOTALL,
)

_MAX_COMPANY_LEN = 80

# Values that describe the document rather than name an organisation.
_GENERIC_COMPANIES = {
    "company", "the company", "our company", "company name",
    "organisation", "the organisation", "organization", "the organization",
    "employer", "the employer", "firm", "the firm",
}

# Document *headings* that a contextual NER model (spaCy in particular) tags as
# ``ORG`` with high confidence -- "OFFER OF EMPLOYMENT", "APPOINTMENT LETTER".
# They name the document, never the hiring organisation, so accepting one as a
# company name poisons the company-verification analyzer with fiction.  Only
# rejected when written in the all-caps block style real headings use, so a
# genuine name that merely contains a word like "Employment" survives.
_DOCUMENT_TITLE_WORDS = (
    "offer", "employment", "appointment", "contract", "letter", "agreement",
    "certificate", "acknowledgment", "acknowledgement", "undertaking", "notice",
    "joining", "intimation", "confirmation", "declaration", "affidavit",
    "memorandum", "proforma", "pro-forma", "application", "nomination",
    "experience", "internship", "training", "resume", "curriculum vitae",
)

# Bare generic nouns that contextual NER models frequently tag as ``ORG``.  A
# single word like "Software" names a field, not an employer, so accepting it
# as a company is the same class of error as accepting a document heading.
_GENERIC_NON_COMPANY = {
    "software", "hardware", "engineering", "technology", "management",
    "consulting", "services", "solutions", "systems", "analytics", "security",
    "networks", "support", "operations", "finance", "accounts", "sales",
    "marketing", "hr", "it", "admin", "team", "staff", "company", "office",
    "bangalore", "mumbai", "delhi", "hyderabad", "chennai", "pune",
}

# Function words that carry no meaning in a heading, so they are ignored when
# deciding whether every remaining word is a title word.
_FILLER_WORDS = {
    "of", "the", "a", "an", "for", "to", "and", "by", "on", "in", "at", "from",
}


def _is_document_heading(value: str) -> bool:
    """True when *value* reads as a document title rather than a company name.

    Two conditions must both hold, so a genuine all-caps company whose name
    happens to contain a title word (``ACME EMPLOYMENT SOLUTIONS``) is kept:

    * the span is written in capitals, the way headings are typeset; and
    * *every* content word is a title word, so there is no distinguishing token
      left over.  "OFFER OF EMPLOYMENT" qualifies; "ACME EMPLOYMENT SOLUTIONS"
      does not, because "acme" and "solutions" are not title words.
    """
    letters = [ch for ch in value if ch.isalpha()]
    if not letters:
        return False
    if not all(ch.isupper() for ch in letters):
        return False
    tokens = [t for t in re.findall(r"[a-z]+", value.lower()) if t not in _FILLER_WORDS]
    if not tokens:
        return False
    return all(token in _DOCUMENT_TITLE_WORDS for token in tokens)


def _company_from_label(document_text: str) -> str | None:
    """Extract ``Company: X`` style labelled values from *document_text*."""
    match = _COMPANY_LABEL_RE.search(document_text)
    if match is None:
        # Word-processor tables put the label and value on separate lines.
        match = _COMPANY_LABEL_NEXT_LINE_RE.search(document_text)
    if not match:
        return None
    value = match.group("value").strip().strip("*#\"'“”‘’").strip()
    value = _VALUE_CUT_RE.split(value, maxsplit=1)[0].strip()
    value = value.strip(".,;:").strip().strip("*#\"'“”‘’").strip()
    if len(value) > _MAX_COMPANY_LEN:
        value = value[:_MAX_COMPANY_LEN].rsplit(" ", 1)[0]
    return value if _is_plausible_company(value) else None


def _company_from_entities(entities: list[Entity]) -> str | None:
    """Return the first plausible ``ORG`` span produced by the NER engine."""
    for entity in entities:
        if entity.label == "ORG" and _is_plausible_company(entity.text):
            return entity.text.strip()
    return None


def _normalise_url(value: str) -> str | None:
    """Return a fetchable ``http(s)`` URL, or ``None`` if not one."""
    candidate = value.strip().rstrip(".,;:!?)]}\"'")
    if candidate.lower().startswith("www."):
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


def mine_document_fields(document_text: str | None) -> dict[str, str]:
    """Return candidate request fields found in *document_text*.

    Args:
        document_text: Plain text extracted from the uploaded file.

    Returns:
        A mapping of request-field name to extracted value.  Missing
        categories are simply absent — this function never raises and never
        invents values.
    """
    if not document_text or not document_text.strip():
        return {}

    found: dict[str, str] = {}
    try:
        extraction = nlp_entities.extract_entities(document_text)
    except Exception as exc:  # pragma: no cover - extract_entities never raises
        logger.warning("Document field mining skipped, NER failed: %s", exc)
        return found

    for entity in extraction.entities:
        if entity.label == "EMAIL" and "recruiter_email" not in found:
            found["recruiter_email"] = entity.text.strip()
        elif entity.label == "PHONE" and "recruiter_phone" not in found:
            found["recruiter_phone"] = entity.text.strip()
        elif entity.label == "URL" and "url" not in found:
            url = _normalise_url(entity.text)
            if url:
                found["url"] = url

    company = _company_from_label(document_text) or _company_from_entities(
        extraction.entities
    )
    if company:
        found["company_name"] = company

    return found


def fill_missing_fields(
    request: AssessmentRequest, document_text: str | None
) -> list[str]:
    """Fill empty fields on *request* from *document_text*.

    Only fields the user left blank are set — submitted input always wins.

    Args:
        request: The in-flight assessment request (mutated in place).
        document_text: Plain text extracted from the uploaded file.

    Returns:
        The names of the fields that were auto-filled
        (``document_derived_inputs``), in :data:`DERIVABLE_FIELDS` order.
    """
    candidates = mine_document_fields(document_text)
    filled: list[str] = []
    for field_name in DERIVABLE_FIELDS:
        value = candidates.get(field_name)
        if not value:
            continue
        if getattr(request, field_name, None):
            continue  # user typed it — never override
        setattr(request, field_name, value)
        filled.append(field_name)
    if filled:
        logger.info(
            "Document supplied %d missing input field(s): %s",
            len(filled), ", ".join(filled),
        )
    return filled



def _is_plausible_company(value: str) -> bool:
    """True when *value* looks like an organisation name, not noise."""
    cleaned = value.strip()
    if not (2 <= len(cleaned) <= _MAX_COMPANY_LEN):
        return False
    if cleaned.lower() in _GENERIC_COMPANIES:
        return False
    if sum(ch.isalpha() for ch in cleaned) < 2:
        return False
    # Identifiers are other fields' business, not a company name's.
    lowered = cleaned.lower()
    if "@" in cleaned or "://" in cleaned or lowered.startswith("www."):
        return False
    if any(ch.isdigit() for ch in cleaned):
        return False
    # A company name occupies one line.  A span carrying newlines is a NER
    # artefact that ran a sentence and a table row together
    # ("Acme Corp.\nCompany\nAcme Corp") -- never a usable name.
    if "\n" in cleaned or "\r" in cleaned:
        return False
    if _is_document_heading(cleaned):
        return False
    # A bare industry word names a field, not an employer.  Multi-word names
    # are exempt: "Software Solutions Ltd" is a plausible company.
    if len(cleaned.split()) == 1 and cleaned.lower() in _GENERIC_NON_COMPANY:
        return False
    return True
