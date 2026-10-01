"""Tests for the public web-page retrieval and HTML extraction service.

No network access is performed: the tests exercise URL/host safety checks,
the BeautifulSoup (and regex fallback) parsers, and the configuration /
SSRF gates in :func:`app.services.web_retrieval.fetch_page`.
"""

from __future__ import annotations

import pytest

from app.services import web_retrieval

JOB_POSTING_HTML = """
<html>
  <head>
    <title>Senior Engineer - Acme Corp</title>
    <meta name="description" content="Join the Acme Corp engineering team">
  </head>
  <body>
    <h1>Senior Engineer</h1>
    <p>Job description: responsibilities include designing services.</p>
    <p>Requirements: 3+ years experience with Python.</p>
    <form action="/apply" method="post">
      <input type="text" name="full_name">
      <input type="file" name="resume">
    </form>
    <a href="https://acme.example/about-us">About Acme</a>
    <script type="application/ld+json">
      {"@context": "https://schema.org", "@type": "JobPosting", "title": "Senior Engineer"}
    </script>
  </body>
</html>
"""

PAYMENT_HTML = """
<html>
  <head><title>Internship Opportunity</title></head>
  <body>
    <p>Selected candidates must pay a refundable security deposit.</p>
    <p>A one-time training fee of Rs 5000 applies before onboarding.</p>
  </body>
</html>
"""

BENIGN_HTML = """
<html>
  <head><title>Welcome</title></head>
  <body><p>Hello and welcome to our homepage. Browse our products.</p></body>
</html>
"""


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


def test_extract_from_html_detects_job_posting():
    """A genuine listing page is parsed into job-posting metadata."""
    page = web_retrieval.extract_from_html(JOB_POSTING_HTML, "https://acme.example/jobs/1")

    assert page.title == "Senior Engineer - Acme Corp"
    assert page.meta_description == "Join the Acme Corp engineering team"
    assert page.has_job_posting is True
    assert page.json_ld_job_posting is True
    assert page.has_apply_form is True
    assert page.domain == "acme.example"
    assert "acme.example" in page.link_domains
    assert "Job description" in page.text


def test_extract_from_html_detects_payment_solicitation():
    """Payment keywords on a 'careers' page are surfaced as payment terms."""
    page = web_retrieval.extract_from_html(PAYMENT_HTML, "https://scam.example/apply")

    assert "security deposit" in page.payment_terms
    assert "training fee" in page.payment_terms


def test_extract_from_html_benign_page_has_no_signals():
    """A page with no job/payment content yields empty indicators."""
    page = web_retrieval.extract_from_html(BENIGN_HTML, "https://example.com/")

    assert page.has_job_posting is False
    assert page.payment_terms == []
    assert page.title == "Welcome"


def test_extract_from_html_empty_input_is_safe():
    """Empty HTML returns an empty extraction rather than raising."""
    page = web_retrieval.extract_from_html("", "https://example.com/")

    assert page.text == ""
    assert page.has_job_posting is False
    assert page.domain == "example.com"


def test_regex_fallback_parser_matches_beautifulsoup_signals():
    """The dependency-free regex parser detects the same text-level signals."""
    job_page = web_retrieval._parse_html_regex(JOB_POSTING_HTML, "https://acme.example/jobs/1")
    assert job_page.title == "Senior Engineer - Acme Corp"
    assert job_page.has_job_posting is True
    assert "Job description" in job_page.text

    pay_page = web_retrieval._parse_html_regex(PAYMENT_HTML, "https://scam.example/apply")
    assert "security deposit" in pay_page.payment_terms


# ---------------------------------------------------------------------------
# URL / host safety (SSRF)
# ---------------------------------------------------------------------------


def test_normalise_url_adds_scheme_and_rejects_unsupported():
    """Scheme-less URLs are upgraded; non-HTTP(S) schemes are rejected."""
    assert web_retrieval.normalise_url("example.com/jobs/1") == "https://example.com/jobs/1"
    assert web_retrieval.normalise_url("http://example.com") == "http://example.com"
    assert web_retrieval.normalise_url("ftp://example.com/x") is None
    assert web_retrieval.normalise_url("file:///etc/passwd") is None
    assert web_retrieval.normalise_url("") is None
    assert web_retrieval.normalise_url("   ") is None


@pytest.mark.parametrize(
    "host",
    ["localhost", "127.0.0.1", "10.0.0.5", "192.168.1.10", "169.254.169.254", "0.0.0.0", ""],
)
def test_private_and_metadata_hosts_are_blocked(host):
    """Loopback, private, link-local, and metadata hosts are non-public."""
    assert web_retrieval._is_public_host(host) is False


def test_domain_of_extracts_hostname():
    """_domain_of lowercases the hostname and tolerates bad input."""
    assert web_retrieval._domain_of("https://Example.COM/jobs/1") == "example.com"
    assert web_retrieval._domain_of("not a url") == ""


# ---------------------------------------------------------------------------
# fetch_page gating (no network is performed by these tests)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_page_blocks_private_host_without_request():
    """SSRF guard short-circuits before any HTTP request is made."""
    assert await web_retrieval.fetch_page("http://127.0.0.1:9000/internal") is None
    assert await web_retrieval.fetch_page("http://169.254.169.254/latest/meta-data/") is None


@pytest.mark.asyncio
async def test_fetch_page_rejects_non_http_scheme():
    """Non-HTTP(S) schemes never reach the network layer."""
    assert await web_retrieval.fetch_page("ftp://example.com/jobs/1") is None


@pytest.mark.asyncio
async def test_fetch_page_disabled_by_configuration(monkeypatch):
    """When retrieval is disabled, fetch_page is a no-op."""
    from app.config import get_settings

    monkeypatch.setenv("WEB_RETRIEVAL_ENABLED", "false")
    get_settings.cache_clear()
    try:
        assert web_retrieval.is_enabled() is False
        assert await web_retrieval.fetch_page("https://example.com/jobs/1") is None
    finally:
        monkeypatch.delenv("WEB_RETRIEVAL_ENABLED", raising=False)
        get_settings.cache_clear()

    assert web_retrieval.is_enabled() is True
