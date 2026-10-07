"""Job metadata and entity extraction service.

Extracts key job parameters regardless of input source:
- company_name (with graceful fallback to "Unspecified Company")
- job_title (with graceful fallback to "Job Opportunity")
- recruiter_name, recruiter_email, recruiter_phone, recruiter_linkedin, recruiter_contact
- detected_sources (canonical labels matching the UI source badges)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse

from app.models.schemas import AssessmentRequest
from app.services import document_mining, nlp_entities
from app.services.nlp_entities import _EMAIL_RE, _PHONE_RE

logger = logging.getLogger(__name__)

# Canonical source labels
SOURCE_URL = "Job URL / Career Page"
SOURCE_DESCRIPTION = "Pasted Job Description"
SOURCE_DOCUMENT = "Offer Letter / Contract PDF"
SOURCE_RECRUITER = "Recruiter Details"
SOURCE_MESSAGE = "Email / Message"

# LinkedIn profile URL regex
_LINKEDIN_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9_\-%]+",
    re.IGNORECASE,
)

# Explicit job title labels in plain text / markdown
_JOB_TITLE_LABEL_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*#>]+[ \t]*)*"
    r"(?:job\s+title|role|position|designation|job\s+role|title)"
    r"[ \t]*(?::|-|–|—)"
    r"[ \t]*(?P<value>[^\r\n,;|]+)",
)

# Table layout where title label is on one line and value is on the next line
_JOB_TITLE_NEXT_LINE_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*#>]+[ \t]*)*"
    r"(?:job\s+title|role|position|designation|job\s+role)"
    r"[ \t]*:?[ \t]*\r?\n"
    r"[ \t]*(?P<value>[^\r\n,;|]+)",
)

# Contextual phrases introducing a job title
_JOB_TITLE_PHRASE_RE = re.compile(
    r"(?im)\b(?:"
    r"offer\s+(?:of|for)\s+(?:employment\s*[-–—:]\s*)?|"
    r"selected\s+for\s+(?:the\s+)?|"
    r"application\s+for\s+(?:the\s+)?|"
    r"interviewing\s+for\s+(?:the\s+)?|"
    r"offer\s+you\s+(?:a\s+|an\s+)?|"
    r"looking\s+for\s+(?:an?\s+)?|"
    r"hiring\s+(?:an?\s+)?|"
    r"openings?\s+(?:for\s+)?|"
    r"position\s+of\s+"
    r")"
    r"(?P<value>[A-Z][A-Za-z0-9/ &+–-]{2,45}?)"
    r"(?:\s+(?:role|position|internship|job|opening)|\s+at\s+[A-Z]|\s+in\s+[A-Z]|\s*\||\s*\.|\r|\n)",
)

# Common professional job title pattern matches
_COMMON_TITLE_PATTERNS = [
    r"(?i)\b(?:senior|junior|lead|principal|staff|associate|entry[- ]level|remote)?\s*"
    r"(?:software\s+engineer|frontend\s+developer|backend\s+developer|full[- ]stack\s+developer|"
    r"web\s+developer|mobile\s+developer|data\s+scientist|data\s+analyst|data\s+specialist|"
    r"data\s+entry\s+specialist|data\s+entry\s+operator|financial\s+analyst|finance\s+associate|"
    r"accounts\s+assistant|accountant|accounts\s+executive|product\s+manager|project\s+manager|"
    r"ui/ux\s+designer|ux\s+designer|graphic\s+designer|devops\s+engineer|cloud\s+architect|"
    r"security\s+analyst|cybersecurity\s+analyst|qa\s+engineer|test\s+engineer|"
    r"operations\s+assistant|operations\s+specialist|task\s+specialist|"
    r"crypto\s+portfolio\s+&\s+task\s+specialist|crypto\s+task\s+specialist|"
    r"human\s+resources\s+generalist|hr\s+assistant|recruiter|executive\s+assistant|"
    r"virtual\s+assistant|customer\s+support\s+specialist|support\s+representative)\b",
]

# Known brand domains mapping to canonical company names
_DOMAIN_TO_COMPANY = {
    "stripe.com": "Stripe",
    "google.com": "Google",
    "amazon.com": "Amazon",
    "microsoft.com": "Microsoft",
    "apple.com": "Apple",
    "meta.com": "Meta",
    "netflix.com": "Netflix",
    "tcs.com": "Tata Consultancy Services (TCS)",
    "infosys.com": "Infosys",
    "wipro.com": "Wipro",
    "cognizant.com": "Cognizant",
    "accenture.com": "Accenture",
    "capgemini.com": "Capgemini",
    "deloitte.com": "Deloitte",
}

# Known scam / lookalike demo companies
_DEMO_COMPANIES = {
    "apex-global": "Apex Global Careers",
    "excel-careers": "Excel Career Solutions",
    "global-fast": "Global Fast Remote Jobs",
}


@dataclass
class JobMetadata:
    """Consolidated job and recruiter metadata extracted from inputs."""

    company_name: str = "Unspecified Company"
    job_title: str = "Job Opportunity"
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_phone: Optional[str] = None
    recruiter_linkedin: Optional[str] = None
    recruiter_contact: Optional[str] = None
    detected_sources: List[str] = field(default_factory=list)


def _clean_job_title(title: str) -> Optional[str]:
    """Clean and validate an extracted job title string."""
    cleaned = title.strip().strip("*#\"'“”‘’").strip()
    # Remove trailing noise words
    cleaned = re.sub(r"(?i)\s+(?:at|in|with|for|role|position|job)\s*$", "", cleaned).strip()
    cleaned = re.sub(r"[.,;:|]+$", "", cleaned).strip()

    if 3 <= len(cleaned) <= 65 and any(ch.isalpha() for ch in cleaned):
        # Filter out generic non-titles
        lower = cleaned.lower()
        if lower in {"job", "careers", "apply", "opportunity", "opening", "employment", "details"}:
            return None
        return cleaned
    return None


def _extract_title_from_url(url: str) -> Optional[str]:
    """Derive job title from URL pathname / slug."""
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if not path:
            return None
        slug = path.split("/")[-1]
        if not slug or len(slug) < 3:
            return None

        # Clean hyphens and underscores
        words = re.split(r"[-_]", slug)
        # Filter out purely numeric or common URL markers
        meaningful_words = [
            w for w in words
            if w.lower() not in {"job", "jobs", "listing", "apply", "careers", "detail", "view", "p"}
            and not w.isdigit()
        ]
        if not meaningful_words:
            return None

        # Abbreviations mapping
        abbrevs = {
            "spec": "Specialist",
            "eng": "Engineer",
            "dev": "Developer",
            "fin": "Financial",
            "asst": "Assistant",
            "mgr": "Manager",
            "intern": "Intern",
            "sr": "Senior",
            "jr": "Junior",
        }
        formatted_words = [abbrevs.get(w.lower(), w.capitalize()) for w in meaningful_words]
        title = " ".join(formatted_words)
        return _clean_job_title(title)
    except Exception:
        return None


def extract_job_title(
    texts: list[str],
    url: Optional[str] = None,
) -> str:
    """Extract job title from supplied texts and URL with robust fallback."""
    # 1. Search for explicit labels in text
    for text in texts:
        if not text:
            continue
        match = _JOB_TITLE_LABEL_RE.search(text) or _JOB_TITLE_NEXT_LINE_RE.search(text)
        if match:
            candidate = _clean_job_title(match.group("value"))
            if candidate:
                return candidate

    # 2. Search for contextual phrases (e.g. "We are looking for an Entry-Level...")
    for text in texts:
        if not text:
            continue
        match = _JOB_TITLE_PHRASE_RE.search(text)
        if match:
            candidate = _clean_job_title(match.group("value"))
            if candidate:
                return candidate

    # 3. Search for common job title patterns
    for text in texts:
        if not text:
            continue
        for pat in _COMMON_TITLE_PATTERNS:
            match = re.search(pat, text)
            if match:
                candidate = _clean_job_title(match.group(0))
                if candidate:
                    return candidate

    # 4. Search URL slug
    if url:
        from_url = _extract_title_from_url(url)
        if from_url:
            return from_url

    return "Job Opportunity"


def _clean_company_name(name: str) -> Optional[str]:
    """Clean and validate an extracted company name."""
    cleaned = name.strip().strip("*#\"'“”‘’").strip()
    cleaned = re.sub(r"[.,;:|]+$", "", cleaned).strip()

    if document_mining._is_plausible_company(cleaned):
        return cleaned
    return None


def _extract_company_from_url(url: str) -> Optional[str]:
    """Derive company name from URL hostname."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if not netloc:
            return None

        # Direct domain match
        for domain, brand in _DOMAIN_TO_COMPANY.items():
            if netloc == domain or netloc.endswith("." + domain):
                return brand

        # Check demo brands
        for key, brand in _DEMO_COMPANIES.items():
            if key in netloc:
                return brand

        # Generic domain extraction
        parts = netloc.split(".")
        if len(parts) >= 2:
            root = parts[-2]
            if root in {"co", "com", "org", "net", "gov", "edu", "in"} and len(parts) >= 3:
                root = parts[-3]
            # Strip noise words like careers, jobs, hire
            clean_root = re.sub(r"-(?:careers|jobs|hire|corp|global)", "", root)
            words = [w.capitalize() for w in clean_root.split("-") if w]
            if words:
                candidate = " ".join(words)
                if _clean_company_name(candidate):
                    return candidate
    except Exception:
        pass
    return None


def extract_company_name(
    user_company: Optional[str],
    texts: list[str],
    url: Optional[str] = None,
) -> str:
    """Extract company name with priority given to user input."""
    # 1. User typed company name
    if user_company and user_company.strip():
        cleaned = _clean_company_name(user_company)
        if cleaned:
            return cleaned

    # 2. Check labelled company in texts (document or pasted JD)
    for text in texts:
        if not text:
            continue
        labelled = document_mining._company_from_label(text)
        if labelled:
            cleaned = _clean_company_name(labelled)
            if cleaned:
                return cleaned

    # 3. Contextual patterns like "X is hiring", "interviewing with X", "at X"
    for text in texts:
        if not text:
            continue
        # e.g. "Stripe is hiring..."
        match = re.search(r"(?im)^[ \t]*([A-Z][A-Za-z0-9&' -]{2,35})\s+is\s+hiring\b", text)
        if match:
            cleaned = _clean_company_name(match.group(1))
            if cleaned:
                return cleaned

        # e.g. "Join our team at Acme Corp"
        match = re.search(
            r"(?im)\b(?:welcome\s+to|selected\s+for|interviewing\s+with|offer\s+from|join\s+(?:our\s+)?team\s+at)\s+"
            r"([A-Z][A-Za-z0-9&' -]{2,35}(?:Solutions|Careers|Consultancy|Services|Technologies|Consultant|Pvt|Ltd|Inc|Corp|LLC)?)\b",
            text,
        )
        if match:
            cleaned = _clean_company_name(match.group(1))
            if cleaned:
                return cleaned

    # 4. Extract from URL
    if url:
        from_url = _extract_company_from_url(url)
        if from_url:
            return from_url

    # 5. Fallback to NER ORG entity
    for text in texts:
        if not text:
            continue
        try:
            extraction = nlp_entities.extract_entities(text[:5000])
            for ent in extraction.entities:
                if ent.label == "ORG" and document_mining._is_plausible_company(ent.text):
                    cleaned = _clean_company_name(ent.text)
                    if cleaned:
                        return cleaned
        except Exception:
            pass

    return "Unspecified Company"


def extract_recruiter_details(
    request: AssessmentRequest,
    texts: list[str],
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Extract recruiter name, email, phone, and LinkedIn URL.

    Returns:
        (recruiter_name, recruiter_email, recruiter_phone, recruiter_linkedin)
    """
    recruiter_name = request.recruiter_name.strip() if request.recruiter_name and request.recruiter_name.strip() else None
    recruiter_email = request.recruiter_email.strip() if request.recruiter_email and request.recruiter_email.strip() else None
    recruiter_phone = request.recruiter_phone.strip() if request.recruiter_phone and request.recruiter_phone.strip() else None
    recruiter_linkedin = None

    all_text = "\n".join(t for t in texts if t)

    # 1. LinkedIn extraction
    match_li = _LINKEDIN_RE.search(all_text)
    if match_li:
        recruiter_linkedin = match_li.group(0).rstrip(".,;:)")

    # Also check if request.url is a LinkedIn profile
    if request.url and "linkedin.com/in/" in request.url.lower():
        recruiter_linkedin = request.url.strip()

    # 2. Email extraction fallback
    if not recruiter_email:
        for match in _EMAIL_RE.finditer(all_text):
            em = match.group(0).strip()
            if em and not em.endswith((".png", ".jpg", ".jpeg", ".svg")):
                recruiter_email = em
                break

    # 3. Phone extraction fallback
    if not recruiter_phone:
        # Check WhatsApp consultant mention e.g. "WhatsApp: +91 9812345678"
        wa_match = re.search(r"(?i)(?:whatsapp|phone|call|contact)[:\s]+(\+?\d[\d\s\-().]{8,}\d)", all_text)
        if wa_match:
            recruiter_phone = wa_match.group(1).strip()
        else:
            for match in _PHONE_RE.finditer(all_text):
                digits = re.findall(r"\d", match.group(0))
                if 10 <= len(digits) <= 15:
                    recruiter_phone = match.group(0).strip()
                    break

    # 4. Name extraction fallback
    if not recruiter_name:
        # Check labeled recruiter name on a single line
        match_label = re.search(
            r"(?im)^[ \t]*(?:[-*#>]+[ \t]*)*"
            r"(?:recruiter|hiring\s+manager|hr\s+manager|consultant|contact(?:\s+person)?)"
            r"[ \t]*(?::|-|–|—)[ \t]*([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,2})",
            all_text,
        )
        if match_label:
            recruiter_name = match_label.group(1).strip().splitlines()[0].strip()
        else:
            # Check e.g. "Alex Vance (@fast_crypto_jobs)"
            handle_match = re.search(r"(?im)\b([A-Z][a-z]+[ \t]+[A-Z][a-z]+)\s*\(@[a-zA-Z0-9_]+\)", all_text)
            if handle_match:
                recruiter_name = handle_match.group(0).strip().splitlines()[0].strip()

    return recruiter_name, recruiter_email, recruiter_phone, recruiter_linkedin


def extract_detected_sources(
    request: AssessmentRequest,
    has_document: bool = False,
    has_recruiter: bool = False,
) -> List[str]:
    """Identify which input source categories were provided."""
    sources: List[str] = []

    if request.url and request.url.strip():
        sources.append(SOURCE_URL)

    if request.description and request.description.strip():
        sources.append(SOURCE_DESCRIPTION)

    if has_document:
        sources.append(SOURCE_DOCUMENT)

    if (
        has_recruiter
        or (request.company_name and request.company_name.strip())
        or (request.recruiter_email and request.recruiter_email.strip())
        or (request.recruiter_name and request.recruiter_name.strip())
        or (request.recruiter_phone and request.recruiter_phone.strip())
    ):
        sources.append(SOURCE_RECRUITER)

    if (
        (request.message and request.message.strip())
        or (request.chat_transcript and request.chat_transcript.strip())
        or (request.message_log and request.message_log.strip())
    ):
        sources.append(SOURCE_MESSAGE)

    if not sources:
        sources.append(SOURCE_DESCRIPTION)

    return sources


def extract_job_metadata(
    request: AssessmentRequest,
    document_text: Optional[str] = None,
    document_filename: Optional[str] = None,
    page_text: Optional[str] = None,
) -> JobMetadata:
    """Consolidate extraction across all input channels."""
    text_pool = [
        request.description or "",
        request.message or "",
        request.chat_transcript or "",
        request.message_log or "",
        document_text or "",
        page_text or "",
    ]

    company_name = extract_company_name(
        user_company=request.company_name,
        texts=text_pool,
        url=request.url,
    )

    job_title = extract_job_title(
        texts=text_pool,
        url=request.url,
    )

    rec_name, rec_email, rec_phone, rec_li = extract_recruiter_details(
        request=request,
        texts=text_pool,
    )

    # Consolidated contact representation
    rec_contact_parts = [p for p in (rec_email, rec_phone, rec_li) if p]
    rec_contact = " • ".join(rec_contact_parts) if rec_contact_parts else None

    has_document = bool(document_text or document_filename)
    has_recruiter = bool(rec_name or rec_email or rec_phone or rec_li)

    detected_sources = extract_detected_sources(
        request=request,
        has_document=has_document,
        has_recruiter=has_recruiter,
    )

    return JobMetadata(
        company_name=company_name,
        job_title=job_title,
        recruiter_name=rec_name,
        recruiter_email=rec_email,
        recruiter_phone=rec_phone,
        recruiter_linkedin=rec_li,
        recruiter_contact=rec_contact,
        detected_sources=detected_sources,
    )
