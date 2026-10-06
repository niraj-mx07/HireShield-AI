"""Tests for User Authentication, Profile, and Assessment History MongoDB Persistence."""

import pytest
import pytest_asyncio
from app.database import connect, disconnect, get_database
from app.models.schemas import UserRegisterRequest, UserLoginRequest
from app.api.routes import (
    signup_user,
    login_user,
    get_user_profile,
    save_user_history,
    get_user_history,
    delete_history_item,
    clear_user_history,
)


@pytest_asyncio.fixture(autouse=True)
async def db_lifecycle():
    """Ensure database is connected for MongoDB testing."""
    await connect()
    yield
    await disconnect()


@pytest.mark.asyncio
async def test_user_signup_and_login_flow():
    """Verify registering a new candidate in MongoDB and logging in."""
    test_email = "test.candidate@hireshield.ai"
    reg_req = UserRegisterRequest(
        name="Test Candidate",
        email=test_email,
        role="Candidate / Job Seeker",
    )
    user_res = await signup_user(reg_req)
    assert user_res.email == test_email
    assert user_res.name == "Test Candidate"
    assert user_res.id.startswith("USR-")

    # Login with same email
    login_req = UserLoginRequest(email=test_email)
    login_res = await login_user(login_req)
    assert login_res.email == test_email
    assert login_res.id == user_res.id

    # Profile lookup
    profile = await get_user_profile(test_email)
    assert profile.email == test_email
    assert profile.name == "Test Candidate"


@pytest.mark.asyncio
async def test_user_history_mongodb_persistence():
    """Verify saving scan history to MongoDB and querying it back."""
    test_email = "persistence.test@hireshield.ai"
    
    # Clean up before
    await clear_user_history(test_email)

    test_scan = {
        "id": "HS-TEST01",
        "jobTitle": "Frontend Architect at Stripe",
        "company": "Stripe",
        "riskScore": 12,
        "score": 12,
        "riskLevel": "low",
        "recommendation": "APPLY",
        "verdict": "APPLY",
        "date": "2026-10-06",
        "scanDate": "Oct 06, 2026 • 12:00 PM",
        "payload": {
            "title": "Frontend Architect at Stripe",
            "score": 12,
            "company": "Stripe",
        },
    }

    # Save to MongoDB
    save_res = await save_user_history(test_email, [test_scan])
    assert save_res["status"] == "ok"
    assert save_res["saved_count"] == 1

    # Fetch from MongoDB
    history_res = await get_user_history(test_email)
    assert history_res["total"] == 1
    item = history_res["history"][0]
    assert item["id"] == "HS-TEST01"
    assert item["company"] == "Stripe"
    assert item["score"] == 12

    # Delete history item
    del_res = await delete_history_item(test_email, "HS-TEST01")
    assert del_res["status"] == "deleted"

    history_empty = await get_user_history(test_email)
    assert history_empty["total"] == 0
