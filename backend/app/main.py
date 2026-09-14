"""HireShield-AI Backend — FastAPI application entry point.

Run locally with::

    cd backend
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as assessment_router
from app.config import get_settings
from app.database import connect, disconnect
from app.services.model_loader import load_job_content_model

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: connect to MongoDB and load models on startup."""
    logger.info("Connecting to MongoDB at %s ...", settings.database_url)
    await connect()
    logger.info("MongoDB connected -- database: %s", settings.database_name)
    load_job_content_model()
    yield
    logger.info("Shutting down — closing MongoDB connection …")
    await disconnect()
    logger.info("Goodbye.")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HireShield-AI",
    description=(
        "Opportunity-credibility assessment API. Evaluates job and internship "
        "listings using hybrid AI/ML, NLP, rule-based risk detection, "
        "document inspection, and independent verification."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the frontend origins specified in configuration.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(assessment_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["system"],
    summary="Health check",
    description="Returns a simple status object to confirm the API is running.",
)
async def health_check():
    """Liveness probe — confirms the API process is up."""
    return {"status": "ok", "service": "hireshield-ai"}
