"""Assessment API routes.

Endpoints
---------
POST /api/v1/assessments
    Submit a new assessment via JSON body (URL / text / details).

POST /api/v1/assessments/upload
    Submit a new assessment with an attached document (multipart/form-data).

GET  /api/v1/assessments/{assessment_id}
    Retrieve a previously generated assessment report.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional


from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.database import get_database
from app.models.schemas import (
    AssessmentRequest,
    AssessmentResponse,
    AssessmentStatus,
    CategoryScore,
    Recommendation,
    RiskBand,
    RiskFactor,
    ScamReportRequest,
    ScamReportResponse,
    UserRegisterRequest,
    UserLoginRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserHistoryItemPayload,
)
from app.services.pipeline import run_assessment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["assessments"])


def _hash_password(password: str) -> str:
    """Hash candidate password using SHA-256 for secure storage."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()



# ---------------------------------------------------------------------------
# POST /api/v1/assessments — JSON submission
# ---------------------------------------------------------------------------

@router.post(
    "/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new risk assessment",
    description=(
        "Submit a job/internship URL, description, company name, and/or "
        "recruiter details for risk analysis. Returns an explainable "
        "0–100 risk score with a recommendation."
    ),
)
async def create_assessment(request: AssessmentRequest) -> AssessmentResponse:
    """Create and run a new risk assessment from JSON input."""
    _validate_has_input(request)
    return await run_assessment(request)


# ---------------------------------------------------------------------------
# POST /api/v1/assessments/upload — multipart with document
# ---------------------------------------------------------------------------

@router.post(
    "/assessments/upload",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create assessment with document upload",
    description=(
        "Submit an assessment with an attached offer letter / PDF alongside "
        "optional text fields. The document is analysed for formatting "
        "anomalies, payment clauses, and consistency."
    ),
)
async def create_assessment_with_upload(
    document: UploadFile = File(..., description="Offer letter or PDF to analyse"),
    url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    recruiter_email: Optional[str] = Form(None),
    recruiter_name: Optional[str] = Form(None),
    recruiter_phone: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    user_email: Optional[str] = Form(None),
    consent_for_external_lookups: bool = Form(False),
) -> AssessmentResponse:
    """Create and run a new risk assessment with a document upload."""
    request = AssessmentRequest(
        url=url,
        description=description,
        company_name=company_name,
        recruiter_email=recruiter_email,
        recruiter_name=recruiter_name,
        recruiter_phone=recruiter_phone,
        message=message,
        user_id=user_id,
        user_email=user_email,
        consent_for_external_lookups=consent_for_external_lookups,
    )

    document_bytes = await document.read()
    return await run_assessment(
        request,
        document_bytes=document_bytes,
        document_filename=document.filename,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/assessments — list recent assessments
# ---------------------------------------------------------------------------

@router.get(
    "/assessments",
    summary="List recent assessments",
    description="Retrieve a paginated list of recent assessment summaries, ordered by newest first.",
)
async def list_assessments(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
):
    """List stored assessments with lightweight summary fields."""
    db = get_database()
    cursor = (
        db.assessments
        .find({}, {
            "_id": 0,
            "id": 1,
            "status": 1,
            "risk_score": 1,
            "risk_band": 1,
            "recommendation": 1,
            "confidence": 1,
            "active_inputs": 1,
            "input_summary": 1,
            "created_at": 1,
            "updated_at": 1,
        })
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    total = await db.assessments.count_documents({})

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "assessments": docs,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/assessments/{assessment_id}
# ---------------------------------------------------------------------------

@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentResponse,
    summary="Retrieve an assessment report",
    description="Look up a previously generated assessment by its ID.",
)
async def get_assessment(assessment_id: str) -> AssessmentResponse:
    """Retrieve a stored assessment by ID."""
    db = get_database()
    doc = await db.assessments.find_one({"id": assessment_id})

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' not found.",
        )

    return AssessmentResponse(
        id=doc["id"],
        status=AssessmentStatus(doc.get("status", "completed")),
        risk_score=doc.get("risk_score", 0.0),
        risk_band=RiskBand(doc.get("risk_band", "low")),
        recommendation=Recommendation(doc.get("recommendation", "HOLD")),
        confidence=doc.get("confidence", 0.0),
        category_scores=[CategoryScore(**cs) for cs in doc.get("category_scores", [])],
        risk_factors=[RiskFactor(**rf) for rf in doc.get("risk_factors", [])],
        active_inputs=doc.get("active_inputs", []),
        created_at=doc.get("created_at"),
    )


# ---------------------------------------------------------------------------
# Community Scam Registry Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/scams/report",
    response_model=ScamReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a verified scam indicator",
    description="Submit a fraudulent UPI ID, recruiter phone number, Telegram handle, or email to the community blacklist.",
)
async def report_scam(report: ScamReportRequest) -> ScamReportResponse:
    """Submit a scam indicator to the community defense database."""
    db = get_database()
    report_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)

    doc = {
        "id": report_id,
        "indicator_type": report.indicator_type.strip().lower(),
        "indicator_value": report.indicator_value.strip().lower(),
        "company_impersonated": report.company_impersonated.strip() if report.company_impersonated else None,
        "description": report.description.strip(),
        "loss_amount": report.loss_amount,
        "reported_at": now,
    }
    await db.scam_reports.insert_one(doc)

    return ScamReportResponse(
        id=report_id,
        indicator_type=doc["indicator_type"],
        indicator_value=doc["indicator_value"],
        company_impersonated=doc["company_impersonated"],
        description=doc["description"],
        loss_amount=doc["loss_amount"],
        reported_at=now,
    )


@router.get(
    "/scams/lookup",
    summary="Lookup a potential scam indicator",
    description="Check whether a phone number, UPI handle, recruiter email, or Telegram handle exists in the scam blacklist.",
)
async def lookup_scam(
    indicator: str = Query(..., min_length=2, description="Indicator value to search (e.g. phone, UPI, email, handle)")
):
    """Search community blacklist for matches."""
    db = get_database()
    clean_val = indicator.strip().lower()
    
    # Case-insensitive substring search
    regex_query = {"indicator_value": {"$regex": clean_val, "$options": "i"}}
    matches = await db.scam_reports.find(regex_query).to_list(length=10)

    found = len(matches) > 0
    return {
        "found": found,
        "query": clean_val,
        "match_count": len(matches),
        "reports": [
            {
                "id": m["id"],
                "indicator_type": m["indicator_type"],
                "indicator_value": m["indicator_value"],
                "company_impersonated": m.get("company_impersonated"),
                "description": m["description"],
                "reported_at": m.get("reported_at"),
            }
            for m in matches
        ],
    }


@router.get(
    "/scams/recent",
    summary="Get recent community scam alerts",
    description="Fetch recent community-reported fraudulent recruitment attempts.",
)
async def get_recent_scams(limit: int = Query(10, ge=1, le=50)):
    """Fetch recent community scam reports."""
    db = get_database()
    cursor = db.scam_reports.find().sort("reported_at", -1).limit(limit)
    reports = await cursor.to_list(length=limit)

    return {
        "count": len(reports),
        "reports": [
            {
                "id": r["id"],
                "indicator_type": r["indicator_type"],
                "indicator_value": r["indicator_value"],
                "company_impersonated": r.get("company_impersonated"),
                "description": r["description"],
                "reported_at": r.get("reported_at"),
            }
            for r in reports
        ],
    }


# ---------------------------------------------------------------------------
# User Authentication & Profile Endpoints (MongoDB)
# ---------------------------------------------------------------------------

@router.post(
    "/auth/signup",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user in MongoDB",
    description="Registers a persistent candidate account in MongoDB.",
)
async def signup_user(req: UserRegisterRequest) -> UserProfileResponse:
    db = get_database()
    clean_email = req.email.strip().lower()
    clean_name = req.name.strip()
    now_str = datetime.now(timezone.utc).isoformat()

    existing = await db.users.find_one({"email": clean_email})
    if existing:
        stats = await _compute_user_stats(db, clean_email)
        return UserProfileResponse(
            id=existing.get("id", f"USR-{uuid.uuid4().hex[:6].upper()}"),
            name=existing.get("name", clean_name),
            email=clean_email,
            role=existing.get("role", "Candidate / Job Seeker"),
            avatar=existing.get("avatar", clean_name[:1].upper() if clean_name else "U"),
            created_at=existing.get("created_at", now_str),
            updated_at=existing.get("updated_at"),
            **stats,
        )

    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    avatar = (req.avatar or clean_name[:1] or "U").upper()
    user_doc = {
        "id": user_id,
        "name": clean_name,
        "email": clean_email,
        "role": req.role or "Candidate / Job Seeker",
        "avatar": avatar,
        "created_at": now_str,
        "updated_at": now_str,
    }
    if req.password:
        user_doc["password_hash"] = _hash_password(req.password)

    try:
        await db.users.insert_one(user_doc)
    except Exception as exc:
        logger.warning("MongoDB user insert error: %s", exc)

    return UserProfileResponse(
        id=user_id,
        name=clean_name,
        email=clean_email,
        role=user_doc["role"],
        avatar=avatar,
        created_at=now_str,
        updated_at=now_str,
        total_scans=0,
        high_risk_scans=0,
        safe_scans=0,
        moderate_scans=0,
    )


@router.post(
    "/auth/login",
    response_model=UserProfileResponse,
    summary="Sign in or auto-provision candidate profile",
    description="Authenticates or auto-provisions a candidate profile in MongoDB.",
)
async def login_user(req: UserLoginRequest) -> UserProfileResponse:
    db = get_database()
    clean_email = req.email.strip().lower()
    now_str = datetime.now(timezone.utc).isoformat()

    existing = await db.users.find_one({"email": clean_email})
    if existing:
        stats = await _compute_user_stats(db, clean_email)
        return UserProfileResponse(
            id=existing.get("id", f"USR-{uuid.uuid4().hex[:6].upper()}"),
            name=existing.get("name", clean_email.split("@")[0].capitalize()),
            email=clean_email,
            role=existing.get("role", "Candidate / Job Seeker"),
            avatar=existing.get("avatar", "U"),
            created_at=existing.get("created_at", now_str),
            updated_at=existing.get("updated_at"),
            **stats,
        )

    prefix = clean_email.split("@")[0].replace(".", " ").replace("_", " ").title()
    name = req.name.strip() if req.name else prefix or "Candidate"
    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    avatar = name[:1].upper() if name else "U"

    user_doc = {
        "id": user_id,
        "name": name,
        "email": clean_email,
        "role": "Candidate / Job Seeker",
        "avatar": avatar,
        "created_at": now_str,
        "updated_at": now_str,
    }
    if req.password:
        user_doc["password_hash"] = _hash_password(req.password)

    try:
        await db.users.insert_one(user_doc)
        stats = await _compute_user_stats(db, clean_email)
    except Exception as exc:
        logger.warning("MongoDB login user auto-provision error: %s", exc)
        stats = {"total_scans": 0, "high_risk_scans": 0, "safe_scans": 0, "moderate_scans": 0}

    return UserProfileResponse(
        id=user_id,
        name=name,
        email=clean_email,
        role=user_doc["role"],
        avatar=avatar,
        created_at=now_str,
        updated_at=now_str,
        **stats,
    )


@router.get(
    "/auth/user/{user_identifier}",
    response_model=UserProfileResponse,
    summary="Get user profile and statistics",
)
async def get_user_profile(user_identifier: str) -> UserProfileResponse:
    db = get_database()
    clean_id = user_identifier.strip().lower()
    user = await db.users.find_one({
        "$or": [{"email": clean_id}, {"id": user_identifier.strip()}]
    })

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_identifier}' not found.",
        )

    user_email = user.get("email", clean_id)
    stats = await _compute_user_stats(db, user_email)

    return UserProfileResponse(
        id=user.get("id", f"USR-{uuid.uuid4().hex[:6].upper()}"),
        name=user.get("name", "Candidate"),
        email=user_email,
        role=user.get("role", "Candidate / Job Seeker"),
        avatar=user.get("avatar", "U"),
        created_at=user.get("created_at", datetime.now(timezone.utc).isoformat()),
        updated_at=user.get("updated_at"),
        **stats,
    )


@router.put(
    "/auth/user/{user_identifier}",
    response_model=UserProfileResponse,
    summary="Update user profile",
)
async def update_user_profile(
    user_identifier: str, req: UserProfileUpdateRequest
) -> UserProfileResponse:
    db = get_database()
    clean_id = user_identifier.strip().lower()
    update_data = {}
    if req.name is not None and req.name.strip():
        update_data["name"] = req.name.strip()
    if req.role is not None and req.role.strip():
        update_data["role"] = req.role.strip()
    if req.avatar is not None and req.avatar.strip():
        update_data["avatar"] = req.avatar.strip()

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.users.update_one(
        {"$or": [{"email": clean_id}, {"id": user_identifier.strip()}]},
        {"$set": update_data},
    )

    return await get_user_profile(user_identifier)


# ---------------------------------------------------------------------------
# User Assessment History Endpoints (MongoDB)
# ---------------------------------------------------------------------------

@router.get(
    "/users/{user_identifier}/history",
    summary="List all assessment history for a specific user from MongoDB",
    description="Fetch persistent scans belonging to this user, sorted newest first.",
)
async def get_user_history(user_identifier: str):
    db = get_database()
    clean_id = user_identifier.strip().lower()

    cursor = db.user_history.find(
        {"$or": [{"user_email": clean_id}, {"user_id": user_identifier.strip()}]},
        {"_id": 0}
    ).sort("created_at", -1)

    items = await cursor.to_list(length=300)
    return {
        "user": user_identifier,
        "total": len(items),
        "history": items,
    }


@router.post(
    "/users/{user_identifier}/history",
    summary="Save or batch sync assessment scans to MongoDB user history",
    description="Persist assessment scan records for this user.",
)
async def save_user_history(user_identifier: str, body: dict | list):
    db = get_database()
    clean_email = user_identifier.strip().lower()
    now_str = datetime.now(timezone.utc).isoformat()

    items = []
    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        if "items" in body and isinstance(body["items"], list):
            items = body["items"]
        else:
            items = [body]

    saved_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id") or f"HS-{uuid.uuid4().hex[:6].upper()}"
        doc = {
            **item,
            "id": item_id,
            "user_email": clean_email,
            "created_at": item.get("created_at") or item.get("date") or now_str,
            "updated_at": now_str,
        }
        await db.user_history.update_one(
            {"id": item_id, "user_email": clean_email},
            {"$set": doc},
            upsert=True,
        )
        saved_count += 1

    return {"status": "ok", "saved_count": saved_count}


@router.delete(
    "/users/{user_identifier}/history/{item_id}",
    summary="Delete a single assessment report from user history in MongoDB",
)
async def delete_history_item(user_identifier: str, item_id: str):
    db = get_database()
    clean_email = user_identifier.strip().lower()

    result = await db.user_history.delete_one({
        "id": item_id,
        "$or": [{"user_email": clean_email}, {"user_id": user_identifier.strip()}],
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"History item '{item_id}' not found for user.",
        )

    return {"status": "deleted", "id": item_id}


@router.delete(
    "/users/{user_identifier}/history",
    summary="Clear all assessment history for a user in MongoDB",
)
async def clear_user_history(user_identifier: str):
    db = get_database()
    clean_email = user_identifier.strip().lower()

    result = await db.user_history.delete_many({
        "$or": [{"user_email": clean_email}, {"user_id": user_identifier.strip()}],
    })

    return {"status": "cleared", "deleted_count": result.deleted_count}


async def _compute_user_stats(db, email: str) -> dict:
    """Helper to compute aggregate scan stats for user profile."""
    scans = await db.user_history.find(
        {"user_email": email},
        {"_id": 0, "riskLevel": 1, "risk_level": 1, "score": 1, "riskScore": 1}
    ).to_list(length=500)
    total = len(scans)
    high = 0
    mod = 0
    safe = 0
    for s in scans:
        lvl = s.get("riskLevel") or s.get("risk_level")
        if not lvl:
            sc = s.get("riskScore", s.get("score", 0))
            lvl = "high" if sc >= 70 else "moderate" if sc >= 35 else "low"
        if lvl == "high":
            high += 1
        elif lvl == "moderate":
            mod += 1
        else:
            safe += 1

    return {
        "total_scans": total,
        "high_risk_scans": high,
        "safe_scans": safe,
        "moderate_scans": mod,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_has_input(request: AssessmentRequest) -> None:
    """Ensure at least one meaningful input field is provided."""
    if not any([
        request.url,
        request.description,
        request.company_name,
        request.recruiter_email,
        request.recruiter_name,
        request.recruiter_phone,
        request.message,
    ]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "At least one input field (url, description, company_name, "
                "recruiter_email, recruiter_name, or message) must be provided."
            ),
        )
