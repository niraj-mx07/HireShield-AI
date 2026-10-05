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
RAW_DIR = ML_DIR / "data" / "raw"
RAW_CSV = RAW_DIR / "fake_job_postings.csv"
RAW_INDIA_CSV = RAW_DIR / "synthetic_indian_jobs.csv"
RAW_CONTRACT_CSV = RAW_DIR / "job_contract_scam_dataset.csv"
RAW_INDIA_JSON = RAW_DIR / "india_job_scams.json"
PROCESSED_DIR = ML_DIR / "data" / "processed"

LABEL_COLUMN = "fraudulent"
TEST_SIZE = 0.20
RANDOM_STATE = 42


def load_raw() -> pd.DataFrame:
    """Load and normalize raw datasets from diverse sources into unified schema."""
    frames: list[pd.DataFrame] = []

    # 1. Global Kaggle Fake Job Postings
    if RAW_CSV.exists():
        df_kaggle = pd.read_csv(RAW_CSV)
        print(f"[INFO] Loaded {len(df_kaggle):,} rows from {RAW_CSV.name}")
        # Standardize text columns
        cols = ["title", "description", "requirements", "company_profile", "benefits"]
        for c in cols:
            df_kaggle[c] = df_kaggle[c].fillna("") if c in df_kaggle.columns else ""
        df_kaggle["combined_text"] = df_kaggle[cols].agg(" ".join, axis=1).str.strip()
        df_kaggle = df_kaggle[["combined_text", "fraudulent"]].dropna(subset=["fraudulent"])
        frames.append(df_kaggle)
    else:
        print(f"[WARNING] Raw CSV not found: {RAW_CSV}")

    # 2. Indian Job Fraud Dataset (Adit Sawhney)
    if RAW_INDIA_CSV.exists():
        df_ind = pd.read_csv(RAW_INDIA_CSV)
        print(f"[INFO] Loaded {len(df_ind):,} rows from {RAW_INDIA_CSV.name}")
        cols = ["title", "company", "description", "requirements", "salary", "contact"]
        for c in cols:
            df_ind[c] = df_ind[c].fillna("") if c in df_ind.columns else ""
        df_ind["combined_text"] = df_ind[cols].agg(" ".join, axis=1).str.strip()
        if "label" in df_ind.columns:
            df_ind["fraudulent"] = df_ind["label"]
        df_ind = df_ind[["combined_text", "fraudulent"]].dropna(subset=["fraudulent"])
        frames.append(df_ind)

    # 3. Contract & Internship Scam Dataset (Sohaib Dev)
    if RAW_CONTRACT_CSV.exists():
        df_contract = pd.read_csv(RAW_CONTRACT_CSV)
        print(f"[INFO] Loaded {len(df_contract):,} rows from {RAW_CONTRACT_CSV.name}")
        cols = ["title", "company_name", "contract_type", "experience_letter_terms", "package_benefits_detail"]
        for c in cols:
            df_contract[c] = df_contract[c].fillna("") if c in df_contract.columns else ""
        df_contract["combined_text"] = df_contract[cols].agg(" ".join, axis=1).str.strip()
        if "is_fraudulent" in df_contract.columns:
            df_contract["fraudulent"] = df_contract["is_fraudulent"]
        df_contract = df_contract[["combined_text", "fraudulent"]].dropna(subset=["fraudulent"])
        frames.append(df_contract)

    # 4. India Job Scams curated JSON
    if RAW_INDIA_JSON.exists():
        df_json = pd.read_json(RAW_INDIA_JSON)
        print(f"[INFO] Loaded {len(df_json):,} rows from {RAW_INDIA_JSON.name}")
        cols = ["title", "description", "requirements", "company_profile", "benefits"]
        for c in cols:
            df_json[c] = df_json[c].fillna("") if c in df_json.columns else ""
        df_json["combined_text"] = df_json[cols].agg(" ".join, axis=1).str.strip()
        df_json = df_json[["combined_text", "fraudulent"]].dropna(subset=["fraudulent"])
        frames.append(df_json)

    # 5. Modern Remote Work, Messaging & Tech Startup JSON
    raw_modern_json = RAW_DIR / "modern_scams_and_startups.json"
    if raw_modern_json.exists():
        df_modern = pd.read_json(raw_modern_json)
        print(f"[INFO] Loaded {len(df_modern):,} rows from {raw_modern_json.name}")
        cols = ["title", "description", "requirements", "company_profile", "benefits"]
        for c in cols:
            df_modern[c] = df_modern[c].fillna("") if c in df_modern.columns else ""
        df_modern["combined_text"] = df_modern[cols].agg(" ".join, axis=1).str.strip()
        df_modern = df_modern[["combined_text", "fraudulent"]].dropna(subset=["fraudulent"])
        frames.append(df_modern)

    # 6. Parameter-Based Job Postings Dataset (Financial, Recruiter, Contract, Low-Barrier & Legitimate Counterparts)
    raw_params_json = RAW_DIR / "parameter_based_job_postings.json"
    if raw_params_json.exists():
        df_params = pd.read_json(raw_params_json)
        print(f"[INFO] Loaded {len(df_params):,} rows from {raw_params_json.name}")
        cols = ["title", "description", "requirements", "company_profile", "benefits"]
        for c in cols:
            df_params[c] = df_params[c].fillna("") if c in df_params.columns else ""
        df_params["combined_text"] = df_params[cols].agg(" ".join, axis=1).str.strip()
        df_params = df_params[["combined_text", "fraudulent"]].dropna(subset=["fraudulent"])
        frames.append(df_params)


    if not frames:
        print("[ERROR] No raw data found in ml/data/raw/")
        sys.exit(1)

    df = pd.concat(frames, ignore_index=True)
    print(f"[INFO] Total merged raw rows across all sources: {len(df):,}")
    return df


def combine_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Merge text columns into combined_text if not already constructed."""
    if "combined_text" in df.columns:
        df["combined_text"] = df["combined_text"].fillna("").astype(str).str.strip()
        return df

    text_cols = [c for c in ["title", "description", "requirements", "company_profile", "benefits"] if c in df.columns]
    for col in text_cols:
        df[col] = df[col].fillna("")

    df["combined_text"] = df[text_cols].agg(" ".join, axis=1).str.strip()
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
