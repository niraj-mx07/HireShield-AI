"""Tests for Random Text Robustness and Deployment-Ready Authentication."""

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.database import connect, disconnect, get_database
from app.models.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    AssessmentRequest,
)
from app.api.routes import signup_user, login_user, create_assessment
from app.analyzers import job_content, company_verification, recruiter_verification
from app.utils.security import create_access_token, decode_access_token, verify_password


@pytest_asyncio.fixture(autouse=True)
async def db_lifecycle():
    """Ensure database connection for test suite."""
    await connect()
    yield
    await disconnect()


# =============================================================================
# 1. RANDOM / NONSENSICAL TEXT INPUT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_gibberish_job_content():
    """Verify that keyboard mashing produces an unparseable warning instead of arbitrary scam verdicts."""
    res = await job_content.analyze(description="asdfghjkl qwertyuiop zxcvbnm 123456")
    assert res.analyzed is True
    assert any("unverifiable or nonsensical" in rf.description.lower() for rf in res.risk_factors)
    # Calibrated to moderate/neutral
    assert 40.0 <= res.score <= 65.0


@pytest.mark.asyncio
async def test_conversational_query_job_content():
    """Verify that a candidate asking a question is recognized as an inquiry."""
    res = await job_content.analyze(description="Is this job legit? Can you please check if it is a scam?")
    assert res.analyzed is True
    assert any("conversational prompt or question" in rf.description.lower() for rf in res.risk_factors)
    assert res.score <= 30.0


@pytest.mark.asyncio
async def test_random_short_company_does_not_false_match_enterprise():
    """Verify that typing random letters like 'a' or 'age' does not match Infosys or Google."""
    res = await company_verification.analyze(company_name="a")
    assert res.analyzed is True
    # Should NOT match Infosys or any enterprise
    assert not any("verified official corporate portal" in rf.description.lower() for rf in res.risk_factors)
    assert any("random or invalid" in rf.description.lower() for rf in res.risk_factors)

    # Legitimate enterprise still matches properly
    res_google = await company_verification.analyze(company_name="Google LLC")
    assert any("recognized registered enterprise" in rf.description.lower() for rf in res_google.risk_factors)


@pytest.mark.asyncio
async def test_invalid_recruiter_email_and_gibberish_name():
    """Verify that malformed email strings and gibberish names are flagged cleanly."""
    res = await recruiter_verification.analyze(
        recruiter_email="not_a_valid_email_address",
        recruiter_name="asdfgh zxcvbn",
    )
    assert res.analyzed is True
    assert any("invalid recruiter email" in rf.description.lower() for rf in res.risk_factors)
    assert any("random or invalid text" in rf.description.lower() for rf in res.risk_factors)


# =============================================================================
# 2. AUTHENTICATION & JWT DEPLOYMENT READINESS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_jwt_token_generation_and_decoding():
    """Verify HS256 JWT generation, signing, and verification."""
    token = create_access_token({"sub": "USR-12345", "email": "dev@hireshield.ai", "role": "Candidate"})
    assert token is not None
    assert token.count(".") == 2

    claims = decode_access_token(token)
    assert claims is not None
    assert claims["sub"] == "USR-12345"
    assert claims["email"] == "dev@hireshield.ai"
    assert "exp" in claims


@pytest.mark.asyncio
async def test_auth_signup_and_password_login():
    """Verify signup with password produces JWT and enforces password on login."""
    email = "secure.candidate@hireshield.ai"
    password = "SuperSecretPassword123!"

    # Clean up any leftover from previous runs
    db = get_database()
    await db.users.delete_many({"email": email})

    # 1. Signup
    reg_req = UserRegisterRequest(
        name="Secure Candidate",
        email=email,
        password=password,
    )
    signup_res = await signup_user(reg_req)
    assert signup_res.email == email
    assert signup_res.access_token is not None
    assert signup_res.token_type == "bearer"

    # 2. Login with correct password
    login_req_good = UserLoginRequest(email=email, password=password)
    login_res = await login_user(login_req_good)
    assert login_res.email == email
    assert login_res.access_token is not None

    # 3. Login with wrong password -> raises 401 Unauthorized
    login_req_bad = UserLoginRequest(email=email, password="WrongPassword!")
    with pytest.raises(HTTPException) as exc_info:
        await login_user(login_req_bad)
    assert exc_info.value.status_code == 401
    assert "invalid credentials" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_duplicate_signup_raises_409():
    """Verify that signing up with an already registered email raises 409 Conflict."""
    email = "duplicate.test@hireshield.ai"
    db = get_database()
    await db.users.delete_many({"email": email})

    reg_req = UserRegisterRequest(
        name="Original User",
        email=email,
        password="Pass1234!",
    )
    res = await signup_user(reg_req)
    assert res.email == email

    with pytest.raises(HTTPException) as exc_info:
        await signup_user(reg_req)
    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail.lower()
