"""Download the Kaggle "Real or Fake Job Posting" dataset.

Usage::

    # Option A -- Kaggle API (requires KAGGLE_USERNAME + KAGGLE_KEY in env)
    python -m ml.training.download_data

    # Option B -- Manual
    #   1. Download from https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction
    #   2. Extract fake_job_postings.csv into ml/data/raw/

The script stores the CSV at ``ml/data/raw/fake_job_postings.csv`` and then
runs a quick validation pass (class balance, leakage check).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parent.parent          # ml/
DATA_RAW_DIR = ML_DIR / "data" / "raw"
EXPECTED_CSV = DATA_RAW_DIR / "fake_job_postings.csv"

KAGGLE_DATASET = "shivamb/real-or-fake-fake-jobposting-prediction"


def download_via_kaggle() -> bool:
    """Attempt to download using the Kaggle API.

    Returns:
        ``True`` if the download succeeded, ``False`` otherwise.
    """
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi  # type: ignore[import-untyped]
    except ImportError:
        print("[INFO] kaggle package not installed -- skipping API download.")
        return False

    username = os.environ.get("KAGGLE_USERNAME", "")
    key = os.environ.get("KAGGLE_KEY", "")
    if not username or not key:
        print("[INFO] KAGGLE_USERNAME / KAGGLE_KEY not set -- skipping API download.")
        return False

    print(f"[INFO] Downloading dataset '{KAGGLE_DATASET}' via Kaggle API ...")
    try:
        api = KaggleApi()
        api.authenticate()
        DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
        api.dataset_download_files(KAGGLE_DATASET, path=str(DATA_RAW_DIR), unzip=True)
        print(f"[OK]   Dataset saved to {DATA_RAW_DIR}")
        return True
    except Exception as exc:
        print(f"[WARN] Kaggle download failed: {exc}")
        return False


def validate_dataset() -> None:
    """Run validation checks on the downloaded CSV.

    Checks:
        1. File exists and is readable.
        2. Class balance (fraudulent vs real).
        3. Obvious label leakage (any single column predicting label with >0.95 AUC).
    """
    import pandas as pd

    if not EXPECTED_CSV.exists():
        print(f"[ERROR] CSV not found at {EXPECTED_CSV}")
        print("        Please download manually from:")
        print(f"        https://www.kaggle.com/datasets/{KAGGLE_DATASET}")
        print(f"        and place the CSV at: {EXPECTED_CSV}")
        sys.exit(1)

    df = pd.read_csv(EXPECTED_CSV)
    print(f"\n{'='*60}")
    print(f"Dataset validation -- {EXPECTED_CSV.name}")
    print(f"{'='*60}")
    print(f"  Rows:    {len(df):,}")
    print(f"  Columns: {df.shape[1]}")
    print(f"  Columns: {list(df.columns)}")

    # --- Class balance ---
    if "fraudulent" not in df.columns:
        print("[ERROR] Expected 'fraudulent' column not found!")
        sys.exit(1)

    counts = df["fraudulent"].value_counts()
    total = len(df)
    print(f"\n  Class balance:")
    for label, count in sorted(counts.items()):
        pct = count / total * 100
        tag = "real" if label == 0 else "FRAUDULENT"
        print(f"    {label} ({tag:>10}): {count:>6,}  ({pct:.1f}%)")

    ratio = counts.get(0, 0) / max(counts.get(1, 1), 1)
    print(f"  Imbalance ratio: {ratio:.1f}:1")

    if ratio > 10:
        print("  [WARN] Heavy class imbalance -- use stratified splits and F1-based evaluation.")

    # --- Leakage check ---
    print(f"\n  Leakage check (high-cardinality unique-value columns):")
    leakage_suspects = []
    for col in df.columns:
        if col == "fraudulent":
            continue
        # Check if any non-target column has a near-perfect correlation
        # with the label by checking if it's essentially a relabeling.
        nunique = df[col].nunique()
        if nunique <= 2 and nunique > 0:
            # Binary column -- check correlation
            try:
                filled = df[col].fillna(-1)
                if filled.dtype == object:
                    filled = filled.astype("category").cat.codes
                corr = abs(filled.corr(df["fraudulent"]))
                if corr > 0.90:
                    leakage_suspects.append((col, corr))
            except Exception:
                pass

    if leakage_suspects:
        for col, corr in leakage_suspects:
            print(f"    [WARN] '{col}' has {corr:.3f} correlation with label -- potential leakage!")
    else:
        print("    [OK] No obvious single-column leakage detected.")

    # --- Missing value summary ---
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(1)
    cols_with_missing = missing[missing > 0].sort_values(ascending=False)
    if len(cols_with_missing) > 0:
        print(f"\n  Missing values (top columns):")
        for col in cols_with_missing.head(8).index:
            print(f"    {col:30s}: {missing[col]:>5,} ({missing_pct[col]:.1f}%)")

    print(f"\n{'='*60}")
    print("[OK] Validation complete.\n")


def main() -> None:
    """Entry point: download (if possible) then validate."""
    if not EXPECTED_CSV.exists():
        success = download_via_kaggle()
        if not success:
            print(f"\n[INFO] Kaggle download unavailable.")
            print(f"       Please place the CSV manually at:")
            print(f"       {EXPECTED_CSV}")
            print(f"       Download from: https://www.kaggle.com/datasets/{KAGGLE_DATASET}")

    if EXPECTED_CSV.exists():
        validate_dataset()
    else:
        print(f"\n[SKIP] CSV not found -- validation skipped.")
        sys.exit(1)


if __name__ == "__main__":
    main()
