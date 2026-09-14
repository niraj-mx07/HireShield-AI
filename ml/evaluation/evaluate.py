"""Evaluate a saved model on the held-out test set.

Loads the best model and TF-IDF vectoriser from ``ml/artifacts/``, runs
inference on the test split, and prints a full classification report with
confusion matrix.

Usage::

    python -m ml.evaluation.evaluate

This is a standalone evaluation script -- it can be re-run at any time
without re-training, as long as the artifacts and test CSV exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
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
TEST_CSV = ML_DIR / "data" / "processed" / "test.csv"
ARTIFACTS_DIR = ML_DIR / "artifacts"
EVAL_DIR = ML_DIR / "evaluation"

LABEL_COLUMN = "fraudulent"
TEXT_COLUMN = "combined_text"


def load_assets():
    """Load the saved model, vectoriser, and test data."""
    vec_path = ARTIFACTS_DIR / "tfidf_vectorizer.joblib"
    model_path = ARTIFACTS_DIR / "best_model.joblib"

    for path in (vec_path, model_path, TEST_CSV):
        if not path.exists():
            print(f"[ERROR] Required file not found: {path}")
            sys.exit(1)

    vectorizer = joblib.load(vec_path)
    model = joblib.load(model_path)
    test_df = pd.read_csv(TEST_CSV)
    test_df[TEXT_COLUMN] = test_df[TEXT_COLUMN].fillna("")

    print(f"[INFO] Loaded model from {model_path.name}")
    print(f"[INFO] Loaded vectoriser from {vec_path.name}")
    print(f"[INFO] Test set: {len(test_df):,} rows")
    return vectorizer, model, test_df


def evaluate(vectorizer, model, test_df: pd.DataFrame) -> dict:
    """Run evaluation and print results."""
    X_test = vectorizer.transform(test_df[TEXT_COLUMN])
    y_test = test_df[LABEL_COLUMN].values
    y_pred = model.predict(X_test)

    prec = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
    rec = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_test, y_pred, pos_label=1, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    report = classification_report(y_test, y_pred, target_names=["real", "fraud"])

    print(f"\n{'='*60}")
    print("Evaluation Results (on held-out test set)")
    print(f"{'='*60}")
    print(f"  Precision (fraud): {prec:.4f}")
    print(f"  Recall    (fraud): {rec:.4f}")
    print(f"  F1        (fraud): {f1:.4f}")
    print(f"\n  Confusion matrix:")
    print(f"                  Predicted")
    print(f"                  Real   Fraud")
    print(f"    Actual Real   {cm[0][0]:>5}   {cm[0][1]:>5}")
    print(f"    Actual Fraud  {cm[1][0]:>5}   {cm[1][1]:>5}")
    print(f"\n{report}")

    return {
        "precision_fraud": round(prec, 4),
        "recall_fraud": round(rec, 4),
        "f1_fraud": round(f1, 4),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }


def main() -> None:
    """Load, evaluate, and save."""
    vectorizer, model, test_df = load_assets()
    metrics = evaluate(vectorizer, model, test_df)

    # Update metrics.json with standalone eval results
    metrics_path = EVAL_DIR / "metrics.json"
    existing = {}
    if metrics_path.exists():
        with open(metrics_path) as f:
            existing = json.load(f)

    existing["standalone_evaluation"] = metrics
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"[OK]   Metrics updated -> {metrics_path}")


if __name__ == "__main__":
    main()
