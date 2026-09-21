"""Evaluate a saved model on the held-out test set.

Supports both the baseline (TF-IDF + classifier) and the boosted pipeline
(BoostedModelWrapper). Automatically detects the model type and runs the
appropriate evaluation path.

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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parent.parent
TEST_CSV = ML_DIR / "data" / "processed" / "test.csv"
ARTIFACTS_DIR = ML_DIR / "artifacts"
EVAL_DIR = ML_DIR / "evaluation"
PLOTS_DIR = EVAL_DIR / "plots"

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

    # Detect model type
    model_type = type(model).__name__
    is_boosted = model_type == "BoostedModelWrapper"

    print(f"[INFO] Loaded model from {model_path.name} (type: {model_type})")
    print(f"[INFO] Pipeline: {'Boosted' if is_boosted else 'Baseline'}")
    print(f"[INFO] Loaded vectoriser from {vec_path.name}")
    print(f"[INFO] Test set: {len(test_df):,} rows")
    return vectorizer, model, test_df, is_boosted


def evaluate(vectorizer, model, test_df: pd.DataFrame, is_boosted: bool) -> dict:
    """Run evaluation and print results.

    For boosted models, pass raw text directly to the model wrapper.
    For baseline models, use the vectorizer + model separately.
    """
    y_test = test_df[LABEL_COLUMN].values
    texts = test_df[TEXT_COLUMN]

    if is_boosted:
        # BoostedModelWrapper handles the full pipeline from raw text
        y_pred = model.predict(texts)
        if hasattr(model, "predict_proba"):
            y_proba = model.predict_proba(texts)[:, 1]
        else:
            y_proba = y_pred.astype(float)
    else:
        # Baseline: vectorizer.transform -> model.predict
        X_test = vectorizer.transform(texts)
        y_pred = model.predict(X_test)
        if hasattr(model, "predict_proba"):
            y_proba = model.predict_proba(X_test)[:, 1]
        elif hasattr(model, "decision_function"):
            y_proba = model.decision_function(X_test)
        else:
            y_proba = y_pred.astype(float)

    prec = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
    rec = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_test, y_pred, pos_label=1, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=["real", "fraud"])

    # AUC metrics
    try:
        roc_auc = roc_auc_score(y_test, y_proba)
        pr_auc = average_precision_score(y_test, y_proba)
    except Exception:
        roc_auc = 0.0
        pr_auc = 0.0

    print(f"\n{'='*60}")
    print("Evaluation Results (on held-out test set)")
    print(f"{'='*60}")
    print(f"  Precision (fraud): {prec:.4f}")
    print(f"  Recall    (fraud): {rec:.4f}")
    print(f"  F1        (fraud): {f1:.4f}")
    print(f"  ROC-AUC:           {roc_auc:.4f}")
    print(f"  PR-AUC:            {pr_auc:.4f}")
    print(f"\n  Confusion matrix:")
    print(f"                  Predicted")
    print(f"                  Real   Fraud")
    print(f"    Actual Real   {cm[0][0]:>5}   {cm[0][1]:>5}")
    print(f"    Actual Fraud  {cm[1][0]:>5}   {cm[1][1]:>5}")
    print(f"\n{report}")

    # Generate evaluation plots
    generate_eval_plots(y_test, y_proba, y_pred, cm)

    return {
        "precision_fraud": round(prec, 4),
        "recall_fraud": round(rec, 4),
        "f1_fraud": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }


def generate_eval_plots(
    y_test: np.ndarray,
    y_proba: np.ndarray,
    y_pred: np.ndarray,
    cm: np.ndarray,
) -> None:
    """Generate ROC curve, PR curve, and confusion matrix heatmap."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", palette="muted")

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

    # 1. ROC Curve
    try:
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        roc_auc = roc_auc_score(y_test, y_proba)
        axes[0].plot(fpr, tpr, color="#2b5c8f", lw=2, label=f"ROC (AUC = {roc_auc:.4f})")
        axes[0].plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
        axes[0].set_title("ROC Curve", pad=10, fontweight="bold")
        axes[0].set_xlabel("False Positive Rate")
        axes[0].set_ylabel("True Positive Rate")
        axes[0].legend(loc="lower right", frameon=True)
        axes[0].set_xlim(0, 1)
        axes[0].set_ylim(0, 1.02)
    except Exception:
        axes[0].text(0.5, 0.5, "N/A", ha="center", va="center")

    # 2. Precision-Recall Curve
    try:
        prec_arr, rec_arr, _ = precision_recall_curve(y_test, y_proba)
        pr_auc = average_precision_score(y_test, y_proba)
        axes[1].plot(rec_arr, prec_arr, color="#d9534f", lw=2, label=f"PR (AUC = {pr_auc:.4f})")
        axes[1].set_title("Precision-Recall Curve", pad=10, fontweight="bold")
        axes[1].set_xlabel("Recall")
        axes[1].set_ylabel("Precision")
        axes[1].legend(loc="lower left", frameon=True)
        axes[1].set_xlim(0, 1)
        axes[1].set_ylim(0, 1.02)
    except Exception:
        axes[1].text(0.5, 0.5, "N/A", ha="center", va="center")

    # 3. Confusion Matrix Heatmap
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Real", "Fraud"],
        yticklabels=["Real", "Fraud"],
        ax=axes[2],
        cbar=False,
        annot_kws={"size": 14, "weight": "bold"},
    )
    axes[2].set_title("Confusion Matrix", pad=10, fontweight="bold")
    axes[2].set_xlabel("Predicted")
    axes[2].set_ylabel("Actual")

    plt.tight_layout()
    plot_path = PLOTS_DIR / "evaluation_curves.png"
    plt.savefig(plot_path, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"[OK]   Evaluation plots saved -> {plot_path}")


def main() -> None:
    """Load, evaluate, and save."""
    vectorizer, model, test_df, is_boosted = load_assets()
    metrics = evaluate(vectorizer, model, test_df, is_boosted)

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
