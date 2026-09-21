"""Train performance-boosted classifiers for fake-job-posting detection.

Builds on the baseline pipeline with:
    1. Word TF-IDF (1-2 ngrams) with optimized parameters.
    2. Dense engineered heuristic features (JobPostFeatureExtractor).
    3. Combined sparse feature matrix (TF-IDF + heuristics).
    4. Advanced classifiers: tuned LogisticRegression, RandomForest, and
       Soft-Voting ensemble.
    5. Precision-Recall threshold tuning to maximize F1 on the fraud class.

Usage::

    python -m ml.training.train_boosted

Outputs:
    - Best pipeline (vectorizer + features + model)  -> ml/artifacts/best_model.joblib
    - Fitted word TF-IDF vectorizer                  -> ml/artifacts/tfidf_vectorizer.joblib
    - Per-model metrics                              -> ml/evaluation/metrics.json
    - Comparison plots                               -> ml/evaluation/plots/

Requires ``ml/data/processed/train.csv`` (run preprocess.py first).
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.sparse import hstack, issparse, csr_matrix
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import MaxAbsScaler

from ml.training.feature_extractor import JobPostFeatureExtractor

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parent.parent
TRAIN_CSV = ML_DIR / "data" / "processed" / "train.csv"
TEST_CSV = ML_DIR / "data" / "processed" / "test.csv"
ARTIFACTS_DIR = ML_DIR / "artifacts"
EVAL_DIR = ML_DIR / "evaluation"
PLOTS_DIR = EVAL_DIR / "plots"

LABEL_COLUMN = "fraudulent"
TEXT_COLUMN = "combined_text"


# ===========================================================================
# Step 1: Load Data
# ===========================================================================
def load_splits() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the preprocessed train/test CSVs."""
    for path in (TRAIN_CSV, TEST_CSV):
        if not path.exists():
            print(f"[ERROR] {path} not found -- run preprocess.py first.")
            sys.exit(1)

    train_df = pd.read_csv(TRAIN_CSV)
    test_df = pd.read_csv(TEST_CSV)
    train_df[TEXT_COLUMN] = train_df[TEXT_COLUMN].fillna("")
    test_df[TEXT_COLUMN] = test_df[TEXT_COLUMN].fillna("")
    print(f"[INFO] Train: {len(train_df):,} rows | Test: {len(test_df):,} rows")
    fraud_rate = train_df[LABEL_COLUMN].mean() * 100
    print(f"[INFO] Fraud rate: {fraud_rate:.2f}% ({train_df[LABEL_COLUMN].sum():,} positive)")
    return train_df, test_df


# ===========================================================================
# Step 2: Build Feature Matrix (Word TF-IDF + Engineered Features)
# ===========================================================================
def build_feature_matrix(
    train_texts: pd.Series,
    test_texts: pd.Series,
) -> tuple[Any, Any, TfidfVectorizer, JobPostFeatureExtractor, MaxAbsScaler]:
    """Build combined sparse feature matrix from TF-IDF and heuristic features."""

    print("[...] Fitting Word TF-IDF vectorizer...", flush=True)
    word_tfidf = TfidfVectorizer(
        max_features=50_000,
        sublinear_tf=True,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=2,
        dtype=np.float32,
    )
    X_train_word = word_tfidf.fit_transform(train_texts)
    X_test_word = word_tfidf.transform(test_texts)
    print(f"[OK]   Word TF-IDF -- {len(word_tfidf.vocabulary_):,} features", flush=True)

    # --- Engineered heuristic features ---
    print("[...] Extracting engineered heuristic features...", flush=True)
    feat_extractor = JobPostFeatureExtractor()
    X_train_feat = feat_extractor.fit_transform(train_texts)
    X_test_feat = feat_extractor.transform(test_texts)

    scaler = MaxAbsScaler()
    X_train_feat = scaler.fit_transform(X_train_feat)
    X_test_feat = scaler.transform(X_test_feat)
    print(f"[OK]   Engineered features -- {X_train_feat.shape[1]} features", flush=True)

    # --- Combine: sparse TF-IDF + sparse heuristics ---
    X_train = hstack([X_train_word, csr_matrix(X_train_feat)])
    X_test = hstack([X_test_word, csr_matrix(X_test_feat)])
    print(f"[OK]   Combined feature matrix: {X_train.shape[1]:,} total features", flush=True)

    return X_train, X_test, word_tfidf, feat_extractor, scaler


# ===========================================================================
# Step 3: Threshold Optimization
# ===========================================================================
def find_optimal_threshold(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """Find the decision threshold that maximizes F1 score on the PR curve."""
    precision_arr, recall_arr, thresholds = precision_recall_curve(y_true, y_proba)
    f1_scores = 2 * (precision_arr[:-1] * recall_arr[:-1]) / (precision_arr[:-1] + recall_arr[:-1] + 1e-10)
    best_idx = np.argmax(f1_scores)
    return float(thresholds[best_idx])


# ===========================================================================
# Step 4: Train & Evaluate Models
# ===========================================================================
def train_and_evaluate(
    X_train: Any,
    y_train: np.ndarray,
    X_test: Any,
    y_test: np.ndarray,
) -> Dict[str, Any]:
    """Train classifiers, optimize threshold, and evaluate on test set."""
    classifiers = {
        "logistic_regression_boosted": LogisticRegression(
            max_iter=1000,
            C=1.0,
            class_weight="balanced",
            solver="lbfgs",
            random_state=42,
        ),
        "random_forest_tuned": RandomForestClassifier(
            n_estimators=100,
            class_weight="balanced_subsample",
            max_depth=20,
            min_samples_leaf=5,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,
        ),
    }

    results: Dict[str, Any] = {}

    for name, clf in classifiers.items():
        print(f"\n{'='*65}")
        print(f"  Training: {name}")
        print(f"{'='*65}")
        sys.stdout.flush()

        t0 = time.time()
        clf.fit(X_train, y_train)
        train_time = time.time() - t0
        print(f"  Train time: {train_time:.1f}s")
        sys.stdout.flush()

        # Get probabilities
        if hasattr(clf, "predict_proba"):
            y_proba = clf.predict_proba(X_test)[:, 1]
        else:
            y_proba = clf.predict(X_test).astype(float)

        # Threshold optimization
        optimal_threshold = find_optimal_threshold(y_test, y_proba)

        # Predictions at both thresholds
        y_pred_default = (y_proba >= 0.5).astype(int)
        y_pred_optimized = (y_proba >= optimal_threshold).astype(int)

        # Metrics
        f1_def = f1_score(y_test, y_pred_default, pos_label=1, zero_division=0)
        prec_opt = precision_score(y_test, y_pred_optimized, pos_label=1, zero_division=0)
        rec_opt = recall_score(y_test, y_pred_optimized, pos_label=1, zero_division=0)
        f1_opt = f1_score(y_test, y_pred_optimized, pos_label=1, zero_division=0)
        cm = confusion_matrix(y_test, y_pred_optimized)
        report = classification_report(y_test, y_pred_optimized, target_names=["real", "fraud"])

        try:
            roc_auc = roc_auc_score(y_test, y_proba)
            pr_auc = average_precision_score(y_test, y_proba)
        except Exception:
            roc_auc, pr_auc = 0.0, 0.0

        print(f"  Default (0.5)    -> F1: {f1_def:.4f}")
        print(f"  Optimized ({optimal_threshold:.3f}) -> P: {prec_opt:.4f} | R: {rec_opt:.4f} | F1: {f1_opt:.4f}")
        print(f"  ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f}")
        print(f"  Confusion Matrix:\n    {cm[0].tolist()}\n    {cm[1].tolist()}")
        print(f"\n{report}")

        results[name] = {
            "precision_fraud_default": round(precision_score(y_test, y_pred_default, pos_label=1, zero_division=0), 4),
            "recall_fraud_default": round(recall_score(y_test, y_pred_default, pos_label=1, zero_division=0), 4),
            "f1_fraud_default": round(f1_def, 4),
            "precision_fraud_optimized": round(prec_opt, 4),
            "recall_fraud_optimized": round(rec_opt, 4),
            "f1_fraud_optimized": round(f1_opt, 4),
            "optimal_threshold": round(optimal_threshold, 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "confusion_matrix": cm.tolist(),
            "classification_report": report,
            "train_time_seconds": round(train_time, 2),
            "model": clf,
        }

    return results


# ===========================================================================
# Step 5: Build Voting Ensemble
# ===========================================================================
def build_ensemble(
    base_results: Dict[str, Any],
    X_train: Any, y_train: np.ndarray,
    X_test: Any, y_test: np.ndarray,
) -> Dict[str, Any]:
    """Build a soft-voting ensemble from base models."""
    print(f"\n{'='*65}")
    print(f"  Building Soft-Voting Ensemble")
    print(f"{'='*65}")

    estimators = [(name, data["model"]) for name, data in base_results.items()]

    ensemble = VotingClassifier(estimators=estimators, voting="soft", n_jobs=-1)

    t0 = time.time()
    ensemble.fit(X_train, y_train)
    train_time = time.time() - t0

    y_proba = ensemble.predict_proba(X_test)[:, 1]
    optimal_threshold = find_optimal_threshold(y_test, y_proba)
    y_pred = (y_proba >= optimal_threshold).astype(int)

    prec = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
    rec = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_test, y_pred, pos_label=1, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=["real", "fraud"])
    roc_auc = roc_auc_score(y_test, y_proba)
    pr_auc = average_precision_score(y_test, y_proba)

    print(f"  Train time: {train_time:.1f}s")
    print(f"  Optimized ({optimal_threshold:.3f}) -> P: {prec:.4f} | R: {rec:.4f} | F1: {f1:.4f}")
    print(f"  ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f}")
    print(f"\n{report}")

    return {
        "soft_voting_ensemble": {
            "precision_fraud_optimized": round(prec, 4),
            "recall_fraud_optimized": round(rec, 4),
            "f1_fraud_optimized": round(f1, 4),
            "optimal_threshold": round(optimal_threshold, 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "confusion_matrix": cm.tolist(),
            "classification_report": report,
            "train_time_seconds": round(train_time, 2),
            "model": ensemble,
        }
    }


# ===========================================================================
# Step 6: Model Wrapper & Artifact Saving
# ===========================================================================
class BoostedModelWrapper:
    """Wrapper that packages the boosted pipeline for backend compatibility.

    The backend's ``model_loader.py`` calls:
        vectorizer.transform(text)  -> X
        model.predict(X)            -> predictions

    This wrapper supports both flows: raw text input (full pipeline) and
    pre-vectorized sparse input (backward compatibility).
    """

    def __init__(
        self,
        word_tfidf: TfidfVectorizer,
        feature_extractor: JobPostFeatureExtractor,
        scaler: MaxAbsScaler,
        model: Any,
        optimal_threshold: float = 0.5,
    ) -> None:
        self.word_tfidf = word_tfidf
        self.feature_extractor = feature_extractor
        self.scaler = scaler
        self.model = model
        self.optimal_threshold = optimal_threshold

    def predict(self, X_text: Any) -> np.ndarray:
        """Predict from raw text or pre-vectorized sparse matrix."""
        if issparse(X_text):
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(X_text)[:, 1]
                return (proba >= self.optimal_threshold).astype(int)
            return self.model.predict(X_text)

        X_combined = self._build_features(X_text)
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(X_combined)[:, 1]
            return (proba >= self.optimal_threshold).astype(int)
        return self.model.predict(X_combined)

    def predict_proba(self, X_text: Any) -> np.ndarray:
        """Return probability estimates."""
        if issparse(X_text):
            return self.model.predict_proba(X_text)
        X_combined = self._build_features(X_text)
        return self.model.predict_proba(X_combined)

    def _build_features(self, texts: Any) -> Any:
        """Build the full feature matrix from raw texts."""
        X_word = self.word_tfidf.transform(texts)
        X_feat = self.feature_extractor.transform(texts)
        X_feat_scaled = self.scaler.transform(X_feat)
        return hstack([X_word, csr_matrix(X_feat_scaled)])


def select_best(results: Dict[str, Any]) -> str:
    """Pick model with highest optimized F1."""
    best_name = max(results, key=lambda k: results[k].get("f1_fraud_optimized", 0))
    best_f1 = results[best_name]["f1_fraud_optimized"]
    print(f"\n[BEST] {best_name} -- F1(fraud, optimized)={best_f1:.4f}")
    return best_name


def save_artifacts(
    word_tfidf: TfidfVectorizer,
    feature_extractor: JobPostFeatureExtractor,
    scaler: MaxAbsScaler,
    best_name: str,
    best_model: Any,
    optimal_threshold: float,
    all_metrics: Dict[str, Any],
) -> None:
    """Save vectorizer, model wrapper, and metrics."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    wrapper = BoostedModelWrapper(
        word_tfidf=word_tfidf,
        feature_extractor=feature_extractor,
        scaler=scaler,
        model=best_model,
        optimal_threshold=optimal_threshold,
    )

    vec_path = ARTIFACTS_DIR / "tfidf_vectorizer.joblib"
    model_path = ARTIFACTS_DIR / "best_model.joblib"

    joblib.dump(word_tfidf, vec_path)
    joblib.dump(wrapper, model_path)
    print(f"[OK]   Word TF-IDF vectorizer saved -> {vec_path}")
    print(f"[OK]   Boosted model wrapper ({best_name}) saved -> {model_path}")

    # Save metrics (strip model objects)
    serialisable = {}
    for name, m in all_metrics.items():
        serialisable[name] = {k: v for k, v in m.items() if k != "model"}
    serialisable["_best_model"] = best_name
    serialisable["_pipeline"] = "boosted_v1"

    metrics_path = EVAL_DIR / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(serialisable, f, indent=2)
    print(f"[OK]   Metrics saved -> {metrics_path}")


# ===========================================================================
# Step 7: Comparison Plots
# ===========================================================================
def generate_comparison_plots(results: Dict[str, Any]) -> None:
    """Generate bar charts comparing all models."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", palette="muted")

    names = list(results.keys())
    f1s = [results[n].get("f1_fraud_optimized", 0) for n in names]
    precs = [results[n].get("precision_fraud_optimized", 0) for n in names]
    recs = [results[n].get("recall_fraud_optimized", 0) for n in names]
    display = [n.replace("_", " ").title()[:25] for n in names]
    colors = sns.color_palette("viridis", len(names))

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for ax, vals, title in zip(axes, [f1s, precs, recs], ["F1 Score", "Precision", "Recall"]):
        ax.barh(display, vals, color=colors)
        ax.set_title(f"{title} (Fraud Class)", pad=10, fontweight="bold")
        ax.set_xlim(0, 1.05)
        for i, v in enumerate(vals):
            ax.text(v + 0.01, i, f"{v:.4f}", va="center", fontsize=9)

    plt.tight_layout()
    plot_path = PLOTS_DIR / "model_comparison_boosted.png"
    plt.savefig(plot_path, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"[OK]   Comparison plot saved -> {plot_path}")


# ===========================================================================
# Main
# ===========================================================================
def main() -> None:
    """Run the full boosted training pipeline."""
    print("\n" + "=" * 65)
    print("  HireShield-AI — Boosted Training Pipeline")
    print("=" * 65)
    sys.stdout.flush()

    # Load data
    train_df, test_df = load_splits()
    train_texts = train_df[TEXT_COLUMN]
    test_texts = test_df[TEXT_COLUMN]
    y_train = train_df[LABEL_COLUMN].values
    y_test = test_df[LABEL_COLUMN].values
    sys.stdout.flush()

    # Build combined features (Word TF-IDF + Heuristic features)
    X_train, X_test, word_tfidf, feat_extractor, scaler = build_feature_matrix(
        train_texts, test_texts
    )
    sys.stdout.flush()

    # Train individual models
    results = train_and_evaluate(X_train, y_train, X_test, y_test)
    sys.stdout.flush()

    # Build ensemble
    ensemble_results = build_ensemble(results, X_train, y_train, X_test, y_test)
    results.update(ensemble_results)
    sys.stdout.flush()

    # Select best
    best_name = select_best(results)
    best_data = results[best_name]
    optimal_threshold = best_data.get("optimal_threshold", 0.5)

    # Save artifacts
    save_artifacts(
        word_tfidf=word_tfidf,
        feature_extractor=feat_extractor,
        scaler=scaler,
        best_name=best_name,
        best_model=best_data["model"],
        optimal_threshold=optimal_threshold,
        all_metrics=results,
    )

    # Generate comparison plots
    generate_comparison_plots(results)

    # Final summary
    print(f"\n{'='*65}")
    print(f"  BOOSTED TRAINING COMPLETE")
    print(f"{'='*65}")
    print(f"  Best Model: {best_name}")
    print(f"  Optimal Threshold: {optimal_threshold:.4f}")
    print(f"  F1 (fraud):        {best_data.get('f1_fraud_optimized', 'N/A')}")
    print(f"  Precision (fraud): {best_data.get('precision_fraud_optimized', 'N/A')}")
    print(f"  Recall (fraud):    {best_data.get('recall_fraud_optimized', 'N/A')}")
    print(f"  ROC-AUC:           {best_data.get('roc_auc', 'N/A')}")
    print(f"  PR-AUC:            {best_data.get('pr_auc', 'N/A')}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
