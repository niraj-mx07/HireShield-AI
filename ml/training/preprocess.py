"""Preprocess the Kaggle fake-job-posting dataset for model training.

Steps:
    1. Load ``ml/data/raw/fake_job_postings.csv``.
    2. Combine text columns (title, description, requirements, company_profile,
       benefits) into a single ``combined_text`` feature.
    3. Drop exact duplicate postings based on ``combined_text``.
    4. Detect and drop near-duplicate postings (normalized alphanumeric text,
       ignoring case, punctuation, and whitespace differences).
    5. Handle missing values and drop empty text rows.
    6. Stratified train / test split (80/20) preserving class distribution.
    7. Save processed splits to ``ml/data/processed/``.

Usage::

    python -m ml.training.preprocess
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parent.parent
RAW_CSV = ML_DIR / "data" / "raw" / "fake_job_postings.csv"
PROCESSED_DIR = ML_DIR / "data" / "processed"

# Text columns to combine into a single feature
TEXT_COLUMNS = ["title", "description", "requirements", "company_profile", "benefits"]

LABEL_COLUMN = "fraudulent"
TEST_SIZE = 0.20
RANDOM_STATE = 42


def load_raw() -> pd.DataFrame:
    """Load the raw CSV; abort if it doesn't exist."""
    if not RAW_CSV.exists():
        print(f"[ERROR] Raw CSV not found: {RAW_CSV}")
        print("        Run download_data.py first or place the file manually.")
        sys.exit(1)

    df = pd.read_csv(RAW_CSV)
    print(f"[INFO] Loaded {len(df):,} rows from {RAW_CSV.name}")
    return df


def combine_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Merge multiple text columns into a single ``combined_text`` field.

    Missing values are replaced with empty strings so the concatenation
    never contains literal ``nan``.
    """
    for col in TEXT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("")

    df["combined_text"] = df[TEXT_COLUMNS].agg(" ".join, axis=1).str.strip()
    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Remove exact and near-duplicate postings before train/test splitting.

    Duplicate postings across train and test sets create artificial feature
    leakage where the model memorizes repeated text snippets.

    Returns:
        Deduplicated DataFrame.
    """
    initial_count = len(df)

    # 1. Exact duplicates on combined_text
    df = df.drop_duplicates(subset=["combined_text"]).copy()
    exact_removed = initial_count - len(df)
    print(f"[INFO] Exact duplicates removed: {exact_removed:,}")

    # 2. Near-duplicates via normalized alphanumeric representation
    def _normalize(text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return " ".join(text.split())

    df["_norm_text"] = df["combined_text"].apply(_normalize)
    before_near = len(df)
    df = df.drop_duplicates(subset=["_norm_text"]).copy()
    near_removed = before_near - len(df)
    print(f"[INFO] Near-duplicates removed (normalized text): {near_removed:,}")

    df = df.drop(columns=["_norm_text"])
    total_removed = exact_removed + near_removed
    print(
        f"[OK]   Deduplication complete: removed {total_removed:,} duplicate/near-duplicate rows "
        f"({len(df):,} remaining)"
    )
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Basic cleaning: drop rows without a label, remove empty texts."""
    before = len(df)
    df = df.dropna(subset=[LABEL_COLUMN])
    df[LABEL_COLUMN] = df[LABEL_COLUMN].astype(int)

    # Drop rows where combined_text is empty or whitespace-only
    df = df[df["combined_text"].str.strip().astype(bool)]
    after = len(df)

    if before != after:
        print(f"[INFO] Dropped {before - after} rows (missing label or empty text)")
    return df


def split_and_save(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified 80/20 split; save both halves as CSVs."""
    train_df, test_df = train_test_split(
        df,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=df[LABEL_COLUMN],
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    train_path = PROCESSED_DIR / "train.csv"
    test_path = PROCESSED_DIR / "test.csv"

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"[OK]   Train set: {len(train_df):,} rows -> {train_path}")
    print(f"[OK]   Test  set: {len(test_df):,} rows -> {test_path}")

    # Print class distribution for both splits
    for name, split in [("Train", train_df), ("Test", test_df)]:
        counts = split[LABEL_COLUMN].value_counts()
        fraud_pct = counts.get(1, 0) / len(split) * 100
        print(f"       {name} -- real: {counts.get(0, 0):,}  fraud: {counts.get(1, 0):,}  ({fraud_pct:.1f}% fraud)")

    return train_df, test_df


def main() -> None:
    """Run the full preprocessing pipeline."""
    df = load_raw()
    df = combine_text_columns(df)
    df = deduplicate(df)
    df = clean(df)
    split_and_save(df)
    print("\n[OK] Preprocessing complete.")


if __name__ == "__main__":
    main()
