"""Train baseline classifiers for fake-job-posting detection.

Models:
    1. Logistic Regression (TF-IDF)
    2. Random Forest (TF-IDF)

The code is structured so that swapping in a transformer-based classifier
later only requires adding a new entry to ``CLASSIFIERS`` and (optionally)
replacing the TF-IDF vectoriser with an embedding pipeline.

Usage::

    python -m ml.training.train_baseline

Outputs:
    - Fitted TF-IDF vectoriser      -> ml/artifacts/tfidf_vectorizer.joblib
    - Best model                     -> ml/artifacts/best_model.joblib
    - Per-model metrics              -> ml/evaluation/metrics.json

Requires ``ml/data/processed/train.csv`` (run preprocess.py first).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parent.parent
TRAIN_CSV = ML_DIR / "data" / "processed" / "train.csv"
TEST_CSV = ML_DIR / "data" / "processed" / "test.csv"
ARTIFACTS_DIR = ML_DIR / "artifacts"
EVAL_DIR = ML_DIR / "evaluation"

LABEL_COLUMN = "fraudulent"
TEXT_COLUMN = "combined_text"

# ---------------------------------------------------------------------------
# Model registry -- add new classifiers here
# ---------------------------------------------------------------------------
CLASSIFIERS: Dict[str, Any] = {
    "logistic_regression": LogisticRegression(
        max_iter=1000,
        class_weight="balanced",   # handle imbalance
        solver="lbfgs",
        random_state=42,
    ),
    "random_forest": RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",   # handle imbalance
        max_depth=None,
        random_state=42,
        n_jobs=-1,
    ),
}


def load_splits() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the preprocessed train/test CSVs."""
    for path in (TRAIN_CSV, TEST_CSV):
        if not path.exists():
            print(f"[ERROR] {path} not found -- run preprocess.py first.")
            sys.exit(1)

    train_df = pd.read_csv(TRAIN_CSV)
    test_df = pd.read_csv(TEST_CSV)
    # Fill any remaining NaN in combined_text
    train_df[TEXT_COLUMN] = train_df[TEXT_COLUMN].fillna("")
    test_df[TEXT_COLUMN] = test_df[TEXT_COLUMN].fillna("")
    print(f"[INFO] Train: {len(train_df):,} rows | Test: {len(test_df):,} rows")
    return train_df, test_df


def build_tfidf(train_texts: pd.Series) -> TfidfVectorizer:
    """Fit a TF-IDF vectoriser on the training corpus.

    Parameters are chosen for a reasonable baseline -- sublinear TF, bigrams,
    and a 50 000-feature cap to keep memory manageable.
    """
    vectorizer = TfidfVectorizer(
        max_features=50_000,
        sublinear_tf=True,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=2,
    )
    vectorizer.fit(train_texts)
    print(f"[OK]   TF-IDF fitted -- vocabulary size: {len(vectorizer.vocabulary_):,}")
    return vectorizer


def train_and_evaluate(
    vectorizer: TfidfVectorizer,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Train each classifier, evaluate on test set, and return metrics.

    Returns:
        A dict keyed by model name, each value containing metrics and the
        fitted model object.
    """
    X_train = vectorizer.transform(train_df[TEXT_COLUMN])
    y_train = train_df[LABEL_COLUMN].values
    X_test = vectorizer.transform(test_df[TEXT_COLUMN])
    y_test = test_df[LABEL_COLUMN].values

    results: Dict[str, Any] = {}

    for name, clf in CLASSIFIERS.items():
        print(f"\n{'='*60}")
        print(f"Training: {name}")
        print(f"{'='*60}")

        t0 = time.time()
        clf.fit(X_train, y_train)
        train_time = time.time() - t0

        y_pred = clf.predict(X_test)

        # Metrics (focus on the fraud class = 1)
        prec = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
        rec = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
        f1 = f1_score(y_test, y_pred, pos_label=1, zero_division=0)
        cm = confusion_matrix(y_test, y_pred).tolist()
        report = classification_report(y_test, y_pred, target_names=["real", "fraud"])

        print(f"  Train time:  {train_time:.1f}s")
        print(f"  Precision (fraud): {prec:.4f}")
        print(f"  Recall    (fraud): {rec:.4f}")
        print(f"  F1        (fraud): {f1:.4f}")
        print(f"  Confusion matrix:\n    {cm[0]}\n    {cm[1]}")
        print(f"\n{report}")

        results[name] = {
            "precision_fraud": round(prec, 4),
            "recall_fraud": round(rec, 4),
            "f1_fraud": round(f1, 4),
            "confusion_matrix": cm,
            "classification_report": report,
            "train_time_seconds": round(train_time, 2),
            "model": clf,  # kept in memory, not serialised to JSON
        }

    return results


def select_best(results: Dict[str, Any]) -> str:
    """Pick the model with the highest F1 score on the fraud class."""
    best_name = max(results, key=lambda k: results[k]["f1_fraud"])
    print(f"\n[BEST] {best_name} -- F1(fraud)={results[best_name]['f1_fraud']:.4f}")
    return best_name


def save_artifacts(
    vectorizer: TfidfVectorizer,
    best_name: str,
    best_model: Any,
    all_metrics: Dict[str, Any],
) -> None:
    """Persist the vectoriser, best model, and metrics."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    vec_path = ARTIFACTS_DIR / "tfidf_vectorizer.joblib"
    model_path = ARTIFACTS_DIR / f"best_model.joblib"

    joblib.dump(vectorizer, vec_path)
    joblib.dump(best_model, model_path)
    print(f"[OK]   Vectoriser saved -> {vec_path}")
    print(f"[OK]   Best model ({best_name}) saved -> {model_path}")

    # Save metrics (strip the non-serialisable model object)
    serialisable = {}
    for name, m in all_metrics.items():
        serialisable[name] = {k: v for k, v in m.items() if k != "model"}
    serialisable["_best_model"] = best_name

    metrics_path = EVAL_DIR / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(serialisable, f, indent=2)
    print(f"[OK]   Metrics saved -> {metrics_path}")


def main() -> None:
    """Run the full training pipeline."""
    train_df, test_df = load_splits()
    vectorizer = build_tfidf(train_df[TEXT_COLUMN])
    results = train_and_evaluate(vectorizer, train_df, test_df)
    best_name = select_best(results)
    save_artifacts(vectorizer, best_name, results[best_name]["model"], results)
    print("\n[OK] Training pipeline complete.\n")


if __name__ == "__main__":
    main()
