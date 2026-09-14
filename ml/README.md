# HireShield-AI — ML Pipeline

End-to-end training pipeline for the fake-job-posting classifier.

## Quick Start

### 1. Get the data

**Option A — Kaggle API** (requires credentials):

```bash
cd ml
cp .env.example .env
# Edit .env with your KAGGLE_USERNAME and KAGGLE_KEY
pip install -r requirements.txt
python -m training.download_data
```

**Option B — Manual download:**

1. Download from [Kaggle](https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction).
2. Place `fake_job_postings.csv` into `ml/data/raw/`.
3. Run validation: `python -m training.download_data`

### 2. Preprocess

```bash
python -m training.preprocess
```

Combines text fields, handles missing values, and creates a stratified
80/20 train/test split at `ml/data/processed/`.

### 3. Train

```bash
python -m training.train_baseline
```

Trains **Logistic Regression** and **Random Forest** with TF-IDF features,
evaluates on the held-out test set, and saves the best model.

### 4. Evaluate (standalone)

```bash
python -m evaluation.evaluate
```

Re-runs evaluation on the test set using the saved artifacts.

## Output

| Artifact | Location |
|---|---|
| TF-IDF vectoriser | `ml/artifacts/tfidf_vectorizer.joblib` |
| Best model | `ml/artifacts/best_model.joblib` |
| Metrics | `ml/evaluation/metrics.json` |

## Dataset notes

- **Source:** [Kaggle — Real or Fake Job Posting](https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction)
- **License:** CC0 (Public Domain)
- **Class balance:** ~4.8% fraudulent (heavily imbalanced, ~20:1 ratio)
- **Handling:** `class_weight="balanced"` in both classifiers; evaluation
  focuses on precision/recall/F1 for the fraud class, not accuracy.

See `ml/data/README.md` for full dataset documentation.

## Adding new models

Add a new entry to `CLASSIFIERS` in `training/train_baseline.py`:

```python
CLASSIFIERS["my_new_model"] = MyClassifier(...)
```

The pipeline will automatically train, evaluate, and include it in model
selection. For transformer-based models, replace the TF-IDF vectoriser
with an embedding pipeline while keeping the same train/evaluate flow.
