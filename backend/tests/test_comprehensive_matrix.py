"""Comprehensive test suite covering all parameters individually and together.

Tests:
1. Individual parameters:
   - Only URL (Safe vs Phishing/Scam)
   - Only Description (Safe vs Advance Fee Scam)
   - Only Company Name (Recognized Enterprise vs Shell Company)
   - Only Recruiter Details (Corporate Email vs Free Webmail)
   - Only Message / Email (Safe vs Telegram Task Scam)
   - Only Document Upload (PDF bytes with equipment check scam)
2. Parameter Combinations:
   - Full Verified Legitimate Opportunity (Microsoft, matching careers URL, corporate email)
   - Impersonation Mismatch (Google claimed, phishing domain, gmail recruiter)
   - Advance Fee & Security Deposit Scam (Indian placement consultancy)
   - Document Upload + Recruiter + Financial Scam Clause
3. Full API Endpoints & Features:
   - POST /api/v1/assessments (JSON validation & assessment creation)
   - POST /api/v1/assessments/upload (Multipart PDF parsing & analysis)
   - GET /api/v1/assessments (List recent scans)
   - GET /api/v1/assessments/{id} (Retrieve scan details)
   - POST /api/v1/reports/scam (Submit scam report)
   - GET /api/v1/reports/scam (List community blacklist)
   - Pipeline Blacklist Cross-reference: Newly reported indicator is matched dynamically
"""

import pytest
import pytest_asyncio
import io
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import connect, disconnect, get_database
from app.models.schemas import (
    AssessmentRequest,
    RiskCategory,
    RiskBand,
    Recommendation,
)
from app.services.pipeline import run_assessment


@pytest_asyncio.fixture(autouse=True)
async def db_lifecycle():
    """Ensure database is connected for tests that require MongoDB."""
    await connect()
    yield
    await disconnect()


# =============================================================================
# 1. PARAMETER ISOLATION TESTS (Individual Parameters)
# =============================================================================

@pytest.mark.asyncio
async def test_individual_url_only():
    """Test providing ONLY a URL."""
    # Official reputable URL
    req_safe = AssessmentRequest(url="https://careers.google.com/jobs/results/12345")
    res_safe = await run_assessment(req_safe)
    assert res_safe.status.value == "completed"
    assert "Job URL" in res_safe.active_inputs
    assert res_safe.risk_score <= 30.0
    url_cat = next(c for c in res_safe.category_scores if c.category == RiskCategory.URL_WEBSITE)
    assert url_cat.analyzed is True

    # Suspicious disposable domain
    req_scam = AssessmentRequest(url="http://google-careers-verify-login.xyz/apply")
    res_scam = await run_assessment(req_scam)
    assert res_scam.risk_score >= 50.0
    url_cat_scam = next(c for c in res_scam.category_scores if c.category == RiskCategory.URL_WEBSITE)
    assert url_cat_scam.score >= 40.0


@pytest.mark.asyncio
async def test_individual_description_only():
    """Test providing ONLY a Job Description."""
    # Legitimate job description
    req_safe = AssessmentRequest(
        description="Senior Backend Engineer needed to build resilient distributed microservices in Python and Go."
    )
    res_safe = await run_assessment(req_safe)
    assert "Job Description" in res_safe.active_inputs
    desc_cat = next(c for c in res_safe.category_scores if c.category == RiskCategory.JOB_CONTENT)
    assert desc_cat.analyzed is True
    assert res_safe.risk_band in (RiskBand.LOW, RiskBand.MODERATE)

    # Scam description with fee demand
    req_scam = AssessmentRequest(
        description="Data Entry typist required. Earn $5,000 weekly. You must transfer a refundable security fee of $250."
    )
    res_scam = await run_assessment(req_scam)
    assert res_scam.risk_score >= 60.0
    fin_cat = next(c for c in res_scam.category_scores if c.category == RiskCategory.FINANCIAL_SCAM)
    assert fin_cat.score >= 35.0


@pytest.mark.asyncio
async def test_individual_company_name_only():
    """Test providing ONLY a Company Name."""
    # Recognized enterprise
    req_enterprise = AssessmentRequest(company_name="Tata Consultancy Services")
    res_enterprise = await run_assessment(req_enterprise)
    assert "Company Name" in res_enterprise.active_inputs
    cmp_cat = next(c for c in res_enterprise.category_scores if c.category == RiskCategory.COMPANY_VERIFICATION)
    assert cmp_cat.analyzed is True
    assert cmp_cat.score <= 25.0

    # Unrecognized / generic shell company
    req_shell = AssessmentRequest(company_name="Global Fast Data Entry Solutions Pvt Ltd")
    res_shell = await run_assessment(req_shell)
    cmp_cat_shell = next(c for c in res_shell.category_scores if c.category == RiskCategory.COMPANY_VERIFICATION)
    assert cmp_cat_shell.analyzed is True
    assert cmp_cat_shell.score >= 30.0


@pytest.mark.asyncio
async def test_individual_recruiter_details_only():
    """Test providing ONLY recruiter email, name, or phone."""
    # Recruiter free email
    req_free = AssessmentRequest(
        recruiter_email="hiring.officer.global@gmail.com",
        recruiter_name="HR Director",
        recruiter_phone="+1 555-0199",
    )
    res_free = await run_assessment(req_free)
    assert "Recruiter Details" in res_free.active_inputs
    rec_cat = next(c for c in res_free.category_scores if c.category == RiskCategory.RECRUITER_VERIFICATION)
    assert rec_cat.analyzed is True
    assert rec_cat.score >= 35.0

    # Recruiter with recognized corporate domain
    req_corp = AssessmentRequest(
        recruiter_email="sarah@microsoft.com",
        recruiter_name="Sarah Connor",
    )
    res_corp = await run_assessment(req_corp)
    rec_cat_corp = next(c for c in res_corp.category_scores if c.category == RiskCategory.RECRUITER_VERIFICATION)
    assert rec_cat_corp.score <= 15.0


@pytest.mark.asyncio
async def test_individual_message_only():
    """Test providing ONLY a direct email or chat message."""
    # Telegram task scam message
    req_msg = AssessmentRequest(
        message="Hello candidate, you are selected! Connect immediately with @task_manager_payout on Telegram."
    )
    res_msg = await run_assessment(req_msg)
    assert "Email / Message" in res_msg.active_inputs
    assert res_msg.risk_score >= 60.0
    assert any("telegram" in rf.description.lower() or "chat" in rf.description.lower() for rf in res_msg.risk_factors)


@pytest.mark.asyncio
async def test_individual_document_upload_only():
    """Test providing ONLY a document (PDF bytes) with check reimbursement scam."""
    scam_pdf_content = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 200 >>\nstream\n"
        b"BT /F1 12 Tf 72 712 Td (OFFER LETTER: Candidate must deposit $2000 equipment check and wire funds.) Tj ET\n"
        b"endstream\nendobj\nxref\n0 5\n0000000000 65535 f \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n500\n%%EOF"
    )
    req = AssessmentRequest()
    res = await run_assessment(
        req,
        document_bytes=scam_pdf_content,
        document_filename="offer_letter.pdf",
    )
    assert any("Document" in inp for inp in res.active_inputs)
    doc_cat = next(cs for cs in res.category_scores if cs.category == RiskCategory.DOCUMENT_ANALYSIS)
    assert doc_cat.analyzed is True


# =============================================================================
# 2. COMBINATION TESTS (Multiple Parameters Together)
# =============================================================================

@pytest.mark.asyncio
async def test_combination_fully_verified_safe():
    """Test combination of Company + Matching Official URL + Matching Recruiter + Professional Description."""
    req = AssessmentRequest(
        company_name="Microsoft",
        url="https://careers.microsoft.com/us/en/job/12345",
        recruiter_email="hiring@microsoft.com",
        recruiter_name="Alex Smith",
        description="Senior Software Engineer to work on cloud platforms with C# and Azure.",
        consent_for_external_lookups=True,
    )
    res = await run_assessment(req)
    assert res.risk_score <= 35.0
    assert res.risk_band == RiskBand.LOW
    assert res.recommendation == Recommendation.APPLY
    cons_cat = next(c for c in res.category_scores if c.category == RiskCategory.INFORMATION_CONSISTENCY)
    assert cons_cat.analyzed is True
    assert cons_cat.score <= 10.0


@pytest.mark.asyncio
async def test_combination_domain_impersonation_mismatch():
    """Test Company claiming to be Google but using lookalike phishing domain and gmail address."""
    req = AssessmentRequest(
        company_name="Google",
        url="https://google-career-portal.org/job-application",
        recruiter_email="google.hiring.officer@gmail.com",
        recruiter_name="Jane Doe",
        description="Data entry clerk for Google. Payout $45/hour.",
        consent_for_external_lookups=True,
    )
    res = await run_assessment(req)
    assert res.risk_score >= 60.0
    assert res.recommendation == Recommendation.DONT_APPLY
    assert any("impersonation" in rf.description.lower() for rf in res.risk_factors)


@pytest.mark.asyncio
async def test_combination_advance_fee_and_deposit():
    """Test Indian placement scam requiring security deposit."""
    req = AssessmentRequest(
        company_name="Excel Career Solutions",
        url="https://excel-careers-india.in/apply",
        recruiter_email="placementfee@gmail.com",
        recruiter_phone="+91 9812345678",
        description="Accounts Assistant. Mandatory INR 5,000 refundable security deposit required prior to interview.",
        message="Please pay INR 5,000 via GPay or UPI to confirm slot.",
        consent_for_external_lookups=True,
    )
    res = await run_assessment(req)
    assert res.risk_score >= 65.0
    assert res.recommendation == Recommendation.DONT_APPLY
    fin_cat = next(c for c in res.category_scores if c.category == RiskCategory.FINANCIAL_SCAM)
    assert fin_cat.score >= 50.0


# =============================================================================
# 3. API ENDPOINTS & SYSTEM FEATURES
# =============================================================================

@pytest.mark.asyncio
async def test_api_post_assessment_and_get_by_id():
    """Test REST API endpoint POST /assessments and GET /assessments/{id}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create assessment
        payload = {
            "company_name": "Tata Consultancy Services",
            "url": "https://tcs.com/careers",
            "description": "Cloud Engineer with experience in AWS and Python.",
            "consent_for_external_lookups": True,
        }
        post_resp = await client.post("/api/v1/assessments", json=payload)
        assert post_resp.status_code == 201
        data = post_resp.json()
        assert "id" in data
        assert data["risk_score"] <= 40.0
        assert data["status"] == "completed"
        assessment_id = data["id"]

        # 2. Retrieve assessment by ID
        get_resp = await client.get(f"/api/v1/assessments/{assessment_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["id"] == assessment_id
        assert get_data["risk_score"] == data["risk_score"]


@pytest.mark.asyncio
async def test_api_assessment_upload_multipart():
    """Test REST API endpoint POST /assessments/upload with multipart file."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake_pdf = io.BytesIO(b"%PDF-1.4 test offer content with no scam clauses")
        files = {"document": ("safe_offer.pdf", fake_pdf, "application/pdf")}
        data = {
            "company_name": "Stripe",
            "url": "https://stripe.com/jobs",
            "consent_for_external_lookups": "true",
        }
        resp = await client.post("/api/v1/assessments/upload", data=data, files=files)
        assert resp.status_code == 201
        res_json = resp.json()
        assert "id" in res_json
        assert res_json["status"] == "completed"


@pytest.mark.asyncio
async def test_api_list_assessments():
    """Test REST API endpoint GET /assessments listing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/assessments?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "assessments" in data
        assert "total" in data
        assert isinstance(data["assessments"], list)


@pytest.mark.asyncio
async def test_api_scam_report_submission_and_cross_reference():
    """Test reporting a scam indicator and having the pipeline immediately flag it."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        scam_email = "known_phisher_987@suspicious-hr-portal.com"

        # 1. Report scam indicator via API
        report_payload = {
            "indicator_type": "email",
            "indicator_value": scam_email,
            "company_impersonated": "Amazon",
            "description": "Recruiter demanded payment for background screening.",
        }
        post_rep = await client.post("/api/v1/scams/report", json=report_payload)
        assert post_rep.status_code == 201

        # 2. Verify it shows up in GET /scams/recent
        list_rep = await client.get("/api/v1/scams/recent")
        assert list_rep.status_code == 200
        all_reps = list_rep.json()["reports"]
        assert any(r["indicator_value"] == scam_email for r in all_reps)

        # 3. Submit a new assessment with that recruiter email
        assess_payload = {
            "company_name": "Amazon",
            "recruiter_email": scam_email,
            "description": "Customer service associate opening.",
            "consent_for_external_lookups": True,
        }
        assess_resp = await client.post("/api/v1/assessments", json=assess_payload)
        assert assess_resp.status_code == 201
        assess_data = assess_resp.json()
        rec_cat = next(c for c in assess_data["category_scores"] if c["category"] == "recruiter_verification")
        # Pipeline must match the community blacklist and flag high risk
        assert rec_cat["score"] >= 90.0
        assert any("blacklist" in rf["description"].lower() or "community" in rf["description"].lower() for rf in assess_data["risk_factors"])

        # Clean up database
        db = get_database()
        await db.scam_reports.delete_many({"indicator_value": scam_email})
