"""Unit tests for job metadata and source extraction (job_metadata.py)."""

from __future__ import annotations

from app.models.schemas import AssessmentRequest
from app.services.job_metadata import (
    SOURCE_DOCUMENT,
    SOURCE_DESCRIPTION,
    SOURCE_MESSAGE,
    SOURCE_RECRUITER,
    SOURCE_URL,
    extract_company_name,
    extract_detected_sources,
    extract_job_metadata,
    extract_job_title,
    extract_recruiter_details,
)


def test_extract_user_provided_company_and_title():
    req = AssessmentRequest(
        company_name="HireShield Security",
        description="Senior Frontend Developer position open.",
        recruiter_name="Alice Smith",
        recruiter_email="alice@hireshield.example.com",
    )
    meta = extract_job_metadata(req)

    assert meta.company_name == "HireShield Security"
    assert "Frontend Developer" in meta.job_title
    assert meta.recruiter_name == "Alice Smith"
    assert meta.recruiter_email == "alice@hireshield.example.com"
    assert SOURCE_RECRUITER in meta.detected_sources
    assert SOURCE_DESCRIPTION in meta.detected_sources


def test_extract_from_document_text():
    doc_text = (
        "OFFER OF EMPLOYMENT\n\n"
        "Company: Apex Global Careers\n"
        "Job Title: Entry-Level Remote Data Specialist\n"
        "Recruiter: Sarah Jenkins\n"
        "Email: recruitment@apex-global-hr.net\n"
        "Contact: +1 555-019-2834\n"
        "LinkedIn: https://www.linkedin.com/in/sarah-jenkins-talent\n"
    )
    req = AssessmentRequest()
    meta = extract_job_metadata(req, document_text=doc_text, document_filename="offer_letter.pdf")

    assert meta.company_name == "Apex Global Careers"
    assert "Data Specialist" in meta.job_title
    assert meta.recruiter_name == "Sarah Jenkins"
    assert meta.recruiter_email == "recruitment@apex-global-hr.net"
    assert meta.recruiter_phone == "+1 555-019-2834"
    assert meta.recruiter_linkedin == "https://www.linkedin.com/in/sarah-jenkins-talent"
    assert SOURCE_DOCUMENT in meta.detected_sources


def test_extract_from_url_slug_and_domain():
    req = AssessmentRequest(
        url="https://stripe.com/jobs/listing/software-engineer-intern",
        description="Build payments infrastructure with us.",
    )
    meta = extract_job_metadata(req)

    assert meta.company_name == "Stripe"
    assert "Software Engineer Intern" in meta.job_title
    assert SOURCE_URL in meta.detected_sources
    assert SOURCE_DESCRIPTION in meta.detected_sources


def test_fallback_when_unspecified():
    req = AssessmentRequest(
        description="Flexible hours. Immediate start. Simple tasks.",
    )
    meta = extract_job_metadata(req)

    # Must NOT be "Hiring Organization"
    assert meta.company_name == "Unspecified Company"
    assert meta.job_title == "Job Opportunity"
    assert meta.recruiter_name is None
    assert meta.recruiter_email is None


def test_all_five_sources_detected():
    req = AssessmentRequest(
        url="https://example.com/jobs/dev",
        description="We are hiring a Full-Stack Developer",
        company_name="Acme Corp",
        recruiter_email="recruiter@acme.example.com",
        message="Please reply to this email to schedule your interview.",
    )
    sources = extract_detected_sources(req, has_document=True, has_recruiter=True)

    assert SOURCE_URL in sources
    assert SOURCE_DESCRIPTION in sources
    assert SOURCE_DOCUMENT in sources
    assert SOURCE_RECRUITER in sources
    assert SOURCE_MESSAGE in sources
