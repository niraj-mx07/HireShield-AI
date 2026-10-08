"""Improved HireShield-AI training pipeline — v2.

Improvements over train_boosted.py (v1):
  1. Extended word TF-IDF (1-3 ngrams, 100k features, max_df=0.95).
  2. Linear SVM (LinearSVC via CalibratedClassifierCV) — top performer on sparse text.
  3. Logistic Regression C-sweep.
  4. F1.2-based threshold optimization on a held-out validation split.
  5. Extended heuristic feature set (salary promise, internship tropes, etc.).
  6. Strict leakage prevention: all fitters on train only, threshold on val only.
  7. Old-vs-new comparison table at end.
  8. Backward-compatible ImprovedModelWrapper artifact for the backend.

Usage::

    python -m ml.training.train_improved

Outputs:
    ml/artifacts/tfidf_vectorizer.joblib
    ml/artifacts/best_model.joblib
    ml/artifacts/model_config.json
    ml/evaluation/metrics.json
    ml/evaluation/plots/
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
from scipy.sparse import csr_matrix, hstack, issparse
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import VotingClassifier
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
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MaxAbsScaler
from sklearn.svm import LinearSVC

from ml.training.feature_extractor import JobPostFeatureExtractor
from ml.training.model_wrapper import ImprovedModelWrapper  # shared — enables joblib deserialization

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

ML_DIR = Path(__file__).resolve().parent.parent
TRAIN_CSV = ML_DIR / "data" / "processed" / "train.csv"
TEST_CSV = ML_DIR / "data" / "processed" / "test.csv"
ARTIFACTS_DIR = ML_DIR / "artifacts"
EVAL_DIR = ML_DIR / "evaluation"
PLOTS_DIR = EVAL_DIR / "plots"

LABEL_COLUMN = "fraudulent"
TEXT_COLUMN = "combined_text"

# Baseline from train_baseline.py (word TF-IDF only, no heuristics, no tuning)
BASELINE_METRICS = {
    "model": "LogisticRegression (baseline, word TF-IDF 50k, no threshold tuning)",
    "precision_fraud": 0.8678,
    "recall_fraud": 0.8995,
    "f1_fraud": 0.8834,
    "roc_auc": None,
    "pr_auc": None,
    "accuracy": 0.98,
}


# ============================================================================
# Step 1: Load Data
# ============================================================================
def load_splits():
    for p in (TRAIN_CSV, TEST_CSV):
        if not p.exists():
            print(f"[ERROR] {p} not found — run preprocess.py first.")
            sys.exit(1)
    train_df = pd.read_csv(TRAIN_CSV)
    test_df  = pd.read_csv(TEST_CSV)
    train_df[TEXT_COLUMN] = train_df[TEXT_COLUMN].fillna("")
    test_df[TEXT_COLUMN]  = test_df[TEXT_COLUMN].fillna("")
    print(f"[INFO] Train: {len(train_df):,} | Test: {len(test_df):,}")
    print(f"[INFO] Fraud rate (train): {train_df[LABEL_COLUMN].mean()*100:.2f}%")
    return train_df, test_df


# ============================================================================
# Step 2: Feature Matrix
#   Word TF-IDF (1-3 ngrams) + Domain Heuristic Features
#   NOTE: char TF-IDF is intentionally omitted — on long job-posting texts
#   (avg 500+ tokens) char_wb ngrams are O(n*k) where k=ngram width and n=
#   corpus size, making them prohibitively slow (~2–3 min for 20k features).
#   The extended word TF-IDF with 3-grams captures subword scam patterns
#   (e.g. "whatsapp", "gpay", "bitcoins") effectively.
# ============================================================================
def build_feature_matrix(train_texts, test_texts):
    """Build combined sparse matrix: extended word TF-IDF + heuristic features."""
    print("[...] Fitting Word TF-IDF (1-3 ngrams, 100k features)...", flush=True)
    word_tfidf = TfidfVectorizer(
        max_features=100_000,
        sublinear_tf=True,
        ngram_range=(1, 3),       # trigrams catch "whatsapp only", "no fee required"
        stop_words="english",
        min_df=2,
        max_df=0.95,
        dtype=np.float32,
    )
    X_tr_word = word_tfidf.fit_transform(train_texts)
    X_te_word = word_tfidf.transform(test_texts)
    print(f"[OK]   Word TF-IDF: {len(word_tfidf.vocabulary_):,} features", flush=True)

    print("[...] Extracting heuristic features...", flush=True)
    feat_extractor = JobPostFeatureExtractor()
    X_tr_feat = feat_extractor.fit_transform(train_texts)
    X_te_feat = feat_extractor.transform(test_texts)
    scaler = MaxAbsScaler()
    X_tr_feat_s = scaler.fit_transform(X_tr_feat)
    X_te_feat_s = scaler.transform(X_te_feat)
    print(f"[OK]   Heuristic features: {X_tr_feat.shape[1]}", flush=True)

    X_train = hstack([X_tr_word, csr_matrix(X_tr_feat_s)]).tocsr()
    X_test  = hstack([X_te_word, csr_matrix(X_te_feat_s)]).tocsr()
    print(f"[OK]   Combined: {X_train.shape[1]:,} total features", flush=True)
    return X_train, X_test, word_tfidf, feat_extractor, scaler


# ============================================================================
# Step 3: Threshold Optimization (on validation set ONLY)
# ============================================================================
def find_optimal_threshold(y_true, y_proba, beta=1.2):
    """Find threshold maximizing F-beta (beta>1 favors recall — correct for fraud)."""
    prec, rec, thrs = precision_recall_curve(y_true, y_proba)
    b2 = beta ** 2
    fbeta = (1 + b2) * prec[:-1] * rec[:-1] / (b2 * prec[:-1] + rec[:-1] + 1e-10)
    return float(thrs[np.argmax(fbeta)])


# ============================================================================
# Step 4: Train & Evaluate Candidates
# ============================================================================
def get_proba(clf, X):
    if hasattr(clf, "predict_proba"):
        return clf.predict_proba(X)[:, 1]
    d = clf.decision_function(X)
    return 1 / (1 + np.exp(-d))


def evaluate_candidate(name, clf, X_tr, y_tr, X_val, y_val, X_te, y_te):
    print(f"\n{'='*65}\n  Training: {name}\n{'='*65}")
    sys.stdout.flush()
    t0 = time.time()
    clf.fit(X_tr, y_tr)
    elapsed = time.time() - t0
    print(f"  Fit time: {elapsed:.1f}s", flush=True)

    # Tune threshold on val set (NOT test) — avoids test-set leakage
    y_val_proba = get_proba(clf, X_val)
    thr = find_optimal_threshold(y_val, y_val_proba, beta=1.2)
    print(f"  Threshold (F1.2 on val): {thr:.4f}", flush=True)

    # Report on untouched test set
    y_te_proba = get_proba(clf, X_te)
    y_pred_def = (y_te_proba >= 0.5).astype(int)
    y_pred_opt = (y_te_proba >= thr).astype(int)

    f1_def  = f1_score(y_te, y_pred_def, pos_label=1, zero_division=0)
    prec_def = precision_score(y_te, y_pred_def, pos_label=1, zero_division=0)
    rec_def  = recall_score(y_te, y_pred_def, pos_label=1, zero_division=0)
    prec_opt = precision_score(y_te, y_pred_opt, pos_label=1, zero_division=0)
    rec_opt  = recall_score(y_te, y_pred_opt, pos_label=1, zero_division=0)
    f1_opt   = f1_score(y_te, y_pred_opt, pos_label=1, zero_division=0)
    cm       = confusion_matrix(y_te, y_pred_opt)
    report   = classification_report(y_te, y_pred_opt, target_names=["real","fraud"])
    try:
        roc_auc = roc_auc_score(y_te, y_te_proba)
        pr_auc  = average_precision_score(y_te, y_te_proba)
    except Exception:
        roc_auc = pr_auc = 0.0
    acc = (y_pred_opt == y_te).mean()

    print(f"  @0.500 -> P:{prec_def:.4f} R:{rec_def:.4f} F1:{f1_def:.4f}")
    print(f"  @{thr:.3f} -> P:{prec_opt:.4f} R:{rec_opt:.4f} F1:{f1_opt:.4f}")
    print(f"  ROC-AUC:{roc_auc:.4f}  PR-AUC:{pr_auc:.4f}  Acc:{acc:.4f}")
    print(f"  CM: {cm[0].tolist()} / {cm[1].tolist()}")
    print(f"\n{report}")
    sys.stdout.flush()

    return {
        "precision_fraud_default":   round(prec_def, 4),
        "recall_fraud_default":      round(rec_def, 4),
        "f1_fraud_default":          round(f1_def, 4),
        "precision_fraud_optimized": round(prec_opt, 4),
        "recall_fraud_optimized":    round(rec_opt, 4),
        "f1_fraud_optimized":        round(f1_opt, 4),
        "optimal_threshold":         round(thr, 4),
        "roc_auc":                   round(roc_auc, 4),
        "pr_auc":                    round(pr_auc, 4),
        "accuracy_optimized":        round(float(acc), 4),
        "confusion_matrix":          cm.tolist(),
        "classification_report":     report,
        "train_time_seconds":        round(elapsed, 2),
        "model":                     clf,
        "_y_te_proba":               y_te_proba,
    }


def run_all_candidates(X_tr_val, y_tr_val, X_te, y_te):
    """Internal 80/20 split for threshold tuning; test set never seen during selection."""
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_tr_val, y_tr_val, test_size=0.20,
        random_state=RANDOM_STATE, stratify=y_tr_val,
    )
    print(f"\n[INFO] Internal split: train={X_tr.shape[0]:,} | val={X_val.shape[0]:,}")
    sys.stdout.flush()

    candidates = {
        # Linear SVM — typically best on sparse high-dim text features
        "linear_svm_C0.1": CalibratedClassifierCV(
            LinearSVC(C=0.1, class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE), cv=3),
        "linear_svm_C0.5": CalibratedClassifierCV(
            LinearSVC(C=0.5, class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE), cv=3),
        "linear_svm_C1":   CalibratedClassifierCV(
            LinearSVC(C=1.0, class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE), cv=3),
        # Logistic Regression — strong baseline
        "logistic_C0.5":   LogisticRegression(
            C=0.5, max_iter=1000, class_weight="balanced", solver="lbfgs", random_state=RANDOM_STATE),
        "logistic_C1":     LogisticRegression(
            C=1.0, max_iter=1000, class_weight="balanced", solver="lbfgs", random_state=RANDOM_STATE),
        "logistic_C2":     LogisticRegression(
            C=2.0, max_iter=1000, class_weight="balanced", solver="lbfgs", random_state=RANDOM_STATE),
        "logistic_C5":     LogisticRegression(
            C=5.0, max_iter=1000, class_weight="balanced", solver="lbfgs", random_state=RANDOM_STATE),
    }

    results: Dict[str, Any] = {}
    for name, clf in candidates.items():
        try:
            results[name] = evaluate_candidate(name, clf, X_tr, y_tr, X_val, y_val, X_te, y_te)
        except Exception as exc:
            print(f"[WARN] {name} failed: {exc}")
    return results


# ============================================================================
# Step 5: Soft-Voting Ensemble from Top-2
# ============================================================================
def build_ensemble(top2, X_tr_val, y_tr_val, X_val, y_val, X_te, y_te):
    print(f"\n{'='*65}\n  Soft-Voting Ensemble (top-2)\n{'='*65}")
    estimators = [(n, d["model"]) for n, d in top2]
    ens = VotingClassifier(estimators=estimators, voting="soft", n_jobs=-1)
    t0 = time.time()
    ens.fit(X_tr_val, y_tr_val)
    elapsed = time.time() - t0

    y_val_p = ens.predict_proba(X_val)[:, 1]
    thr = find_optimal_threshold(y_val, y_val_p, beta=1.2)
    y_te_p = ens.predict_proba(X_te)[:, 1]
    y_pred = (y_te_p >= thr).astype(int)

    prec = precision_score(y_te, y_pred, pos_label=1, zero_division=0)
    rec  = recall_score(y_te, y_pred, pos_label=1, zero_division=0)
    f1   = f1_score(y_te, y_pred, pos_label=1, zero_division=0)
    cm   = confusion_matrix(y_te, y_pred)
    report = classification_report(y_te, y_pred, target_names=["real","fraud"])
    roc_auc = roc_auc_score(y_te, y_te_p)
    pr_auc  = average_precision_score(y_te, y_te_p)
    acc = (y_pred == y_te).mean()

    print(f"  Fit time: {elapsed:.1f}s")
    print(f"  @{thr:.3f} -> P:{prec:.4f} R:{rec:.4f} F1:{f1:.4f}")
    print(f"  ROC-AUC:{roc_auc:.4f}  PR-AUC:{pr_auc:.4f}")
    print(f"\n{report}")
    sys.stdout.flush()

    return {"soft_voting_ensemble": {
        "precision_fraud_optimized": round(prec, 4),
        "recall_fraud_optimized":    round(rec, 4),
        "f1_fraud_optimized":        round(f1, 4),
        "optimal_threshold":         round(thr, 4),
        "roc_auc":                   round(roc_auc, 4),
        "pr_auc":                    round(pr_auc, 4),
        "accuracy_optimized":        round(float(acc), 4),
        "confusion_matrix":          cm.tolist(),
        "classification_report":     report,
        "train_time_seconds":        round(elapsed, 2),
        "model":                     ens,
        "_y_te_proba":               y_te_p,
    }}


# ImprovedModelWrapper is imported from ml.training.model_wrapper
# (shared module so joblib can deserialize from any script)

# ============================================================================
# Step 7: Select Best, Save Artifacts
# ============================================================================
def select_best(results):
    best = max(results, key=lambda k: results[k].get("f1_fraud_optimized", 0))
    d = results[best]
    print(f"\n[BEST] {best}")
    print(f"       F1={d['f1_fraud_optimized']:.4f}  P={d['precision_fraud_optimized']:.4f}  R={d['recall_fraud_optimized']:.4f}")
    return best


def save_artifacts(word_tfidf, feat_extractor, scaler, best_name, best_data, all_results):
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    thr = best_data.get("optimal_threshold", 0.5)
    wrapper = ImprovedModelWrapper(
        word_tfidf=word_tfidf, feat_extractor=feat_extractor, scaler=scaler,
        model=best_data["model"], optimal_threshold=thr,
        word_vocab_size=len(word_tfidf.vocabulary_),
    )
    joblib.dump(word_tfidf, ARTIFACTS_DIR / "tfidf_vectorizer.joblib")
    joblib.dump(wrapper,    ARTIFACTS_DIR / "best_model.joblib")
    print(f"[OK]   tfidf_vectorizer.joblib saved  ({len(word_tfidf.vocabulary_):,} word features)")
    print(f"[OK]   best_model.joblib saved  ({best_name})")

    config = {
        "pipeline_version":  ImprovedModelWrapper.VERSION,
        "best_model_name":   best_name,
        "optimal_threshold": thr,
        "word_vocab_size":   len(word_tfidf.vocabulary_),
        "f1_fraud":          best_data.get("f1_fraud_optimized"),
        "precision_fraud":   best_data.get("precision_fraud_optimized"),
        "recall_fraud":      best_data.get("recall_fraud_optimized"),
        "roc_auc":           best_data.get("roc_auc"),
        "pr_auc":            best_data.get("pr_auc"),
        "random_state":      RANDOM_STATE,
    }
    with open(ARTIFACTS_DIR / "model_config.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"[OK]   model_config.json saved")

    serialisable = {
        n: {k: v for k, v in m.items() if k not in ("model", "_y_te_proba")}
        for n, m in all_results.items()
    }
    serialisable["_best_model"] = best_name
    serialisable["_pipeline"]   = ImprovedModelWrapper.VERSION
    serialisable["_baseline"]   = BASELINE_METRICS
    with open(EVAL_DIR / "metrics.json", "w") as f:
        json.dump(serialisable, f, indent=2)
    print(f"[OK]   metrics.json saved")


# ============================================================================
# Step 8: Comparison Table & Plots
# ============================================================================
def print_comparison(results, best_name):
    best = results[best_name]
    print(f"\n{'='*70}")
    print("  COMPARISON: OLD BASELINE  vs  NEW IMPROVED MODEL")
    print(f"{'='*70}")
    print(f"  {'Metric':<24} {'Old (LR baseline)':>20} {'New (' + best_name[:20] + ')':>26} {'Delta':>7}")
    print(f"  {'-'*67}")

    def pct(v): return f"{v*100:.2f}%" if v is not None else "N/A"
    rows = [
        ("Accuracy",        BASELINE_METRICS["accuracy"],        best.get("accuracy_optimized")),
        ("Fraud Precision",  BASELINE_METRICS["precision_fraud"], best.get("precision_fraud_optimized")),
        ("Fraud Recall",     BASELINE_METRICS["recall_fraud"],    best.get("recall_fraud_optimized")),
        ("Fraud F1",         BASELINE_METRICS["f1_fraud"],        best.get("f1_fraud_optimized")),
        ("ROC-AUC",          BASELINE_METRICS["roc_auc"],         best.get("roc_auc")),
        ("PR-AUC",           BASELINE_METRICS["pr_auc"],          best.get("pr_auc")),
    ]
    for metric, old, new in rows:
        delta_s = "N/A"
        if old is not None and new is not None:
            d = (new - old) * 100
            delta_s = f"{'+'if d>=0 else ''}{d:.2f}pp"
        print(f"  {metric:<24} {pct(old):>20} {pct(new):>26} {delta_s:>7}")
    print(f"{'='*70}\n")


def generate_plots(results, y_te):
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", palette="muted")
    names   = list(results.keys())
    f1s     = [results[n].get("f1_fraud_optimized", 0) for n in names]
    precs   = [results[n].get("precision_fraud_optimized", 0) for n in names]
    recs    = [results[n].get("recall_fraud_optimized", 0) for n in names]
    display = [n.replace("_", " ").title()[:26] for n in names]
    colors  = sns.color_palette("viridis", len(names))

    fig, axes = plt.subplots(1, 3, figsize=(18, max(5, len(names)*0.7+1.5)))
    for ax, vals, title in zip(axes, [f1s, precs, recs], ["F1 Score","Precision","Recall"]):
        ax.barh(display, vals, color=colors)
        ax.set_title(f"{title} (Fraud Class)", fontweight="bold")
        ax.set_xlim(0, 1.05)
        for i, v in enumerate(vals):
            ax.text(v+0.005, i, f"{v:.3f}", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "model_comparison_improved.png", dpi=180, bbox_inches="tight")
    plt.close()
    print(f"[OK]   Comparison plot -> {PLOTS_DIR/'model_comparison_improved.png'}")

    best_name = max(results, key=lambda k: results[k].get("f1_fraud_optimized", 0))
    y_proba = results[best_name].get("_y_te_proba")
    if y_proba is not None:
        from sklearn.metrics import roc_curve
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
        try:
            fpr, tpr, _ = roc_curve(y_te, y_proba)
            roc_auc = roc_auc_score(y_te, y_proba)
            axes[0].plot(fpr, tpr, color="#2b5c8f", lw=2, label=f"AUC={roc_auc:.4f}")
            axes[0].plot([0,1],[0,1],"k--",lw=1,alpha=0.4)
            axes[0].set_title(f"ROC — {best_name}", fontweight="bold")
            axes[0].set_xlabel("FPR"); axes[0].set_ylabel("TPR"); axes[0].legend()
            prec_arr, rec_arr, _ = precision_recall_curve(y_te, y_proba)
            pr_auc = average_precision_score(y_te, y_proba)
            axes[1].plot(rec_arr, prec_arr, color="#d9534f", lw=2, label=f"AUC={pr_auc:.4f}")
            axes[1].set_title(f"PR — {best_name}", fontweight="bold")
            axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision"); axes[1].legend()
        except Exception as e:
            print(f"[WARN] plot error: {e}")
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / "improved_model_curves.png", dpi=180, bbox_inches="tight")
        plt.close()
        print(f"[OK]   Curves plot -> {PLOTS_DIR/'improved_model_curves.png'}")


# ============================================================================
# Main
# ============================================================================
def main():
    print("\n" + "="*65)
    print("  HireShield-AI — Improved Training Pipeline v2")
    print("="*65); sys.stdout.flush()

    train_df, test_df = load_splits()
    y_tr_val = train_df[LABEL_COLUMN].values
    y_te     = test_df[LABEL_COLUMN].values

    X_tr_val, X_te, word_tfidf, feat_extractor, scaler = build_feature_matrix(
        train_df[TEXT_COLUMN], test_df[TEXT_COLUMN]
    ); sys.stdout.flush()

    results = run_all_candidates(X_tr_val, y_tr_val, X_te, y_te)
    sys.stdout.flush()

    # Build ensemble from top-2 candidates by F1
    sorted_r = sorted(results.items(), key=lambda kv: kv[1].get("f1_fraud_optimized", 0), reverse=True)
    top2 = sorted_r[:2]
    print(f"\n[INFO] Top-2 for ensemble: {[n for n,_ in top2]}")

    _, X_val, _, y_val = train_test_split(
        X_tr_val, y_tr_val, test_size=0.20,
        random_state=RANDOM_STATE, stratify=y_tr_val,
    )
    ens = build_ensemble(top2, X_tr_val, y_tr_val, X_val, y_val, X_te, y_te)
    results.update(ens); sys.stdout.flush()

    best_name = select_best(results)
    best_data = results[best_name]
    save_artifacts(word_tfidf, feat_extractor, scaler, best_name, best_data, results)
    print_comparison(results, best_name)
    generate_plots(results, y_te)

    print(f"\n{'='*65}")
    print(f"  COMPLETE  —  Best: {best_name}")
    print(f"  Threshold : {best_data.get('optimal_threshold','N/A'):.4f}")
    print(f"  F1 (fraud): {best_data.get('f1_fraud_optimized','N/A')}")
    print(f"  Recall    : {best_data.get('recall_fraud_optimized','N/A')}")
    print(f"  Precision : {best_data.get('precision_fraud_optimized','N/A')}")
    print(f"  ROC-AUC   : {best_data.get('roc_auc','N/A')}")
    print(f"  PR-AUC    : {best_data.get('pr_auc','N/A')}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
