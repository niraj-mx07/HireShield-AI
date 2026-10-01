"""Public web-page retrieval and structured extraction.

Implements the "verification via HTTP retrieval" capability promised in the
project documentation using ``requests`` for transport and ``BeautifulSoup``
for parsing.  Retrieval is **opt-in**: callers must only invoke
:func:`fetch_page` *after* the user has granted
``consent_for_external_lookups`` (see README §Privacy and Safety Design).

Safety controls
---------------
* Only ``http``/``https`` schemes are accepted.
* Private, loopback, link-local, reserved, and multicast addresses are blocked
  (SSRF protection) — the hostname is resolved and every resolved address is
  checked *before* the request is made and again after redirects.
* Responses are streamed and truncated to ``max_bytes`` to bound memory.
* Hard timeouts, a descriptive ``User-Agent``, and a redirect cap are applied.
* Any failure degrades gracefully to ``None`` — this module never raises.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (compatible; HireShieldBot/1.0; "
    "+https://github.com/niraj-mx07/HireShield-AI) opportunity-verification"
)
DEFAULT_TIMEOUT = 6.0
DEFAULT_MAX_BYTES = 512 * 1024  # 512 KiB
MAX_REDIRECTS = 3
ALLOWED_SCHEMES = frozenset({"http", "https"})

# Content-type fragments we are willing to parse.
PARSEABLE_CONTENT_TYPES = ("html", "text/plain", "xml")

# Signals that a page actually hosts a job / internship posting.
JOB_POSTING_KEYWORDS = (
    "job description", "responsibilities", "qualifications", "requirements",
    "apply now", "apply for", "job opening", "job vacancy", "vacancy",
    "we are hiring", "join our team", "career opportunity", "internship",
    "experience required", "salary", "compensation", "roles and responsibilities",
)
APPLY_FORM_KEYWORDS = ("apply", "upload resume", "upload cv", "submit application")

# Payment prompts that should never appear on a genuine corporate careers page.
PAYMENT_KEYWORDS = (
    "registration fee", "processing fee", "security deposit", "refundable deposit",
    "training fee", "pay now", "upi", "google pay", "phonepe", "paytm",
    "western union", "wire transfer", "crypto", "usdt", "gift card", "cashier check",
)

_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class PageExtraction:
    """Structured representation of a retrieved public web page."""

    url: str
    final_url: str
    domain: str
    status_code: int = 0
    title: str = ""
    meta_description: str = ""
    text: str = ""
    link_domains: list[str] = field(default_factory=list)
    has_job_posting: bool = False
    has_apply_form: bool = False
    payment_terms: list[str] = field(default_factory=list)
    json_ld_job_posting: bool = False


# ---------------------------------------------------------------------------
# URL / host safety helpers
# ---------------------------------------------------------------------------

def is_enabled() -> bool:
    """Return whether external page retrieval is enabled by configuration."""
    from app.config import get_settings

    return bool(get_settings().web_retrieval_enabled)


def normalise_url(url: str) -> Optional[str]:
    """Return a scheme-qualified URL, or ``None`` if it cannot be normalised."""
    if not url or not url.strip():
        return None
    candidate = url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        logger.debug("Rejected non-HTTP(S) URL scheme: %s", parsed.scheme)
        return None
    if not parsed.hostname:
        return None
    return candidate


def _is_public_host(host: str) -> bool:
    """Return ``True`` only when *host* resolves exclusively to public IPs.

    Blocks SSRF targets such as ``localhost``, ``127.0.0.1``, ``10.0.0.0/8``,
    ``169.254.0.0/16`` (cloud metadata), and other non-routable ranges.
    """
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError, OSError):
        logger.debug("Could not resolve host '%s'; treating as non-public.", host)
        return False

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def _domain_of(url: str) -> str:
    """Extract the lowercase hostname from *url* (empty string on failure)."""
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:  # pragma: no cover - defensive
        return ""


# ---------------------------------------------------------------------------
# HTML parsing (BeautifulSoup with a dependency-free fallback)
# ---------------------------------------------------------------------------

def _detect_payment_terms(text_lower: str) -> list[str]:
    """Return the payment/scam keywords present in the page text."""
    return [kw for kw in PAYMENT_KEYWORDS if kw in text_lower]


def _build_extraction(soup, url: str) -> PageExtraction:
    """Populate a :class:`PageExtraction` from a parsed BeautifulSoup tree."""
    title = soup.title.get_text(strip=True) if soup.title else ""

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if meta_tag and meta_tag.get("content"):
        meta_description = str(meta_tag["content"]).strip()

    # JSON-LD structured data — the canonical machine-readable job marker.
    json_ld_job_posting = False
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        payload = script.string or script.get_text() or ""
        if "jobposting" in payload.lower():
            json_ld_job_posting = True
            break

    # Forms: apply / resume-upload controls.
    has_apply_form = False
    for form in soup.find_all("form"):
        form_text = form.get_text(" ", strip=True).lower()
        attrs_blob = " ".join(
            f"{inp.get('type', '')} {inp.get('name', '')} {inp.get('id', '')}"
            for inp in form.find_all(["input", "textarea", "button", "select"])
        ).lower()
        if any(kw in form_text or kw in attrs_blob for kw in APPLY_FORM_KEYWORDS):
            has_apply_form = True
            break
        if "file" in attrs_blob or "password" in attrs_blob:
            has_apply_form = True
            break

    # Outbound link domains (used for footprint checks).
    link_domains: list[str] = []
    for anchor in soup.find_all("a", href=True):
        dom = _domain_of(str(anchor["href"]))
        if dom and dom not in link_domains:
            link_domains.append(dom)

    # Visible body text.
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    text = _WHITESPACE_RE.sub(" ", soup.get_text(" ", strip=True)).strip()
    text_lower = text.lower()

    has_job_posting = json_ld_job_posting or any(
        kw in text_lower for kw in JOB_POSTING_KEYWORDS
    )

    return PageExtraction(
        url=url,
        final_url=url,
        domain=_domain_of(url),
        title=title,
        meta_description=meta_description,
        text=text,
        link_domains=link_domains,
        has_job_posting=has_job_posting,
        has_apply_form=has_apply_form,
        payment_terms=_detect_payment_terms(text_lower),
        json_ld_job_posting=json_ld_job_posting,
    )


def _parse_html_regex(html: str, url: str) -> PageExtraction:
    """Minimal stdlib fallback used when ``beautifulsoup4`` is unavailable."""
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = _WHITESPACE_RE.sub(" ", title_match.group(1)).strip() if title_match else ""
    body = re.sub(r"<(script|style|noscript|template)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    text = _WHITESPACE_RE.sub(" ", body).strip()
    text_lower = text.lower()
    return PageExtraction(
        url=url,
        final_url=url,
        domain=_domain_of(url),
        title=title,
        text=text,
        has_job_posting=any(kw in text_lower for kw in JOB_POSTING_KEYWORDS),
        has_apply_form=any(kw in text_lower for kw in APPLY_FORM_KEYWORDS),
        payment_terms=_detect_payment_terms(text_lower),
    )


def extract_from_html(html: str, url: str) -> PageExtraction:
    """Parse raw HTML into a :class:`PageExtraction`.

    Uses ``BeautifulSoup`` when installed and transparently falls back to a
    regex-based parser otherwise.  This function performs no network I/O and is
    therefore safe to unit-test directly.
    """
    if not html:
        return PageExtraction(url=url, final_url=url, domain=_domain_of(url))
    try:
        from bs4 import BeautifulSoup
    except Exception:
        logger.warning(
            "beautifulsoup4 is not installed; using the regex HTML fallback. "
            "Install 'beautifulsoup4' for full parsing (see requirements.txt)."
        )
        return _parse_html_regex(html, url)
    return _build_extraction(BeautifulSoup(html, "html.parser"), url)


# ---------------------------------------------------------------------------
# Network retrieval
# ---------------------------------------------------------------------------

def _fetch_page_sync(url: str, timeout: float, max_bytes: int) -> Optional[PageExtraction]:
    """Blocking retrieval used by :func:`fetch_page` (runs in a thread)."""
    host = _domain_of(url)
    if not _is_public_host(host):
        logger.warning("Blocked retrieval of non-public host: %s", host)
        return None

    try:
        import requests
    except Exception:  # pragma: no cover - requests is a hard dependency
        logger.error("'requests' is not installed; page retrieval unavailable.")
        return None

    session = requests.Session()
    session.max_redirects = MAX_REDIRECTS
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})

    try:
        with session.get(url, timeout=timeout, allow_redirects=True, stream=True) as resp:
            # Re-validate the post-redirect destination against SSRF.
            final_host = _domain_of(resp.url) or host
            if final_host != host and not _is_public_host(final_host):
                logger.warning("Blocked post-redirect non-public host: %s", final_host)
                return None

            content_type = str(resp.headers.get("Content-Type", "")).lower()
            if content_type and not any(ct in content_type for ct in PARSEABLE_CONTENT_TYPES):
                logger.debug("Skipping non-parseable content type '%s' for %s", content_type, url)
                return None

            raw = bytearray()
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                raw.extend(chunk)
                if len(raw) >= max_bytes:
                    break

            encoding = resp.encoding or "utf-8"
            html = bytes(raw).decode(encoding, errors="ignore")
            extraction = extract_from_html(html, url)
            extraction.status_code = resp.status_code
            extraction.final_url = str(resp.url)
            extraction.domain = final_host
            logger.info(
                "Retrieved %s (%s, %d bytes, job_posting=%s)",
                url, resp.status_code, len(raw), extraction.has_job_posting,
            )
            return extraction
    except Exception as exc:
        logger.info("Page retrieval failed for %s: %s", url, exc)
        return None


async def fetch_page(
    url: str,
    *,
    timeout: Optional[float] = None,
    max_bytes: Optional[int] = None,
) -> Optional[PageExtraction]:
    """Retrieve and parse a public web page without blocking the event loop.

    Args:
        url: Absolute or scheme-less URL to fetch.  Scheme-less values are
            upgraded to ``https://``.
        timeout: Override the default request timeout (seconds).
        max_bytes: Override the default response size cap (bytes).

    Returns:
        A :class:`PageExtraction`, or ``None`` when consent/URL validation
        fails, the host is not public, the response is not HTML, or any
        network error occurs.
    """
    from app.config import get_settings

    settings = get_settings()
    if not settings.web_retrieval_enabled:
        logger.debug("Web retrieval disabled by configuration; skipping %s", url)
        return None

    normalised = normalise_url(url)
    if not normalised:
        return None

    eff_timeout = timeout if timeout is not None else settings.web_retrieval_timeout
    eff_max_bytes = max_bytes if max_bytes is not None else settings.web_retrieval_max_bytes

    return await asyncio.to_thread(_fetch_page_sync, normalised, eff_timeout, eff_max_bytes)

