"""Service for loading and caching machine learning model artifacts.

Loads fitted vectorisers and trained models into memory once at application
startup (or on first use) to avoid per-request I/O latency.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Tuple

import joblib

logger = logging.getLogger(__name__)

# Cached model references
_vectorizer: Any | None = None
_model: Any | None = None
_loaded: bool = False


def _find_artifacts_dir() -> Path:
    """Locate the ml/artifacts directory relative to repo structure or backend."""
    # Try 1: relative from backend/app/services/ (3 levels up -> repo root -> ml/artifacts)
    repo_root = Path(__file__).resolve().parents[3]
    candidate = repo_root / "ml" / "artifacts"
    if candidate.exists():
        return candidate

    # Try 2: relative to current working directory
    cwd_candidate = Path("ml/artifacts").resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    # Try 3: relative to parent of cwd
    parent_candidate = Path("../ml/artifacts").resolve()
    if parent_candidate.exists():
        return parent_candidate

    return candidate


def load_job_content_model() -> Tuple[Any | None, Any | None]:
    """Load the TF-IDF vectoriser and trained model from artifacts.

    If artifact files are missing (e.g. on a fresh checkout prior to
    running training), logs a warning and returns ``(None, None)``
    without raising an exception.

    Returns:
        Tuple of ``(vectorizer, model)`` or ``(None, None)``.
    """
    global _vectorizer, _model, _loaded

    artifacts_dir = _find_artifacts_dir()
    vec_path = artifacts_dir / "tfidf_vectorizer.joblib"
    model_path = artifacts_dir / "best_model.joblib"

    if not vec_path.exists() or not model_path.exists():
        logger.warning(
            "Job content ML artifacts not found at %s. "
            "Analyzers will operate in unanalyzed/stub mode until models are trained.",
            artifacts_dir,
        )
        _loaded = True
        return None, None

    try:
        logger.info("Loading job content ML artifacts from %s ...", artifacts_dir)
        _vectorizer = joblib.load(vec_path)
        _model = joblib.load(model_path)
        _loaded = True
        logger.info("Job content ML model loaded successfully.")
    except Exception as exc:
        logger.warning(
            "Failed to load job content model artifacts: %s. "
            "Falling back to unanalyzed mode.",
            exc,
        )
        _vectorizer = None
        _model = None
        _loaded = True

    return _vectorizer, _model


def get_job_content_model() -> Tuple[Any | None, Any | None]:
    """Return the cached vectoriser and model, loading them if not yet loaded."""
    global _loaded
    if not _loaded:
        return load_job_content_model()
    return _vectorizer, _model
