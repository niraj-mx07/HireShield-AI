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

## Certificate forgery CNN (vision)

A second, image-based model flags forged internship certificates as a **secondary
verification signal** for uploaded documents.

```
ml/
├── notebooks/
│   └── train_certificate_cnn.ipynb     # Kaggle/Colab GPU: train + export ONNX
├── training/
│   └── download_certificates.py        # download, de-duplicate, stratified split
└── artifacts/
    ├── certificate_cnn.onnx            # exported model (backend: onnxruntime)
    └── certificate_cnn.json            # input size, mean/std, classes, threshold
```

### 1. Prepare the data (local)

```bash
pip install -r ml/requirements-vision.txt
python -m ml.training.download_certificates            # downloads via the Kaggle API
python -m ml.training.download_certificates --skip-download   # index only
```

Images land in `ml/data/raw/certificates/` (git-ignored) and a stratified
70/15/15 index plus `summary.json` is written to `ml/data/processed/certificates/`.

### 2. Train on a free GPU

Open `ml/notebooks/train_certificate_cnn.ipynb` on **Kaggle** (add the
`godzilla04/internship-certificates` dataset as an input, enable a GPU) or
**Colab**, then run all cells. It fine-tunes MobileNetV3-Small, tunes a
false-positive-safe threshold, and exports `certificate_cnn.onnx`.

### 3. Ship the artifacts

Copy `certificate_cnn.onnx` + `certificate_cnn.json` into `ml/artifacts/`
(the `.json` sidecar is read at runtime, so the threshold can change without code
edits). The backend only needs `onnxruntime` — never PyTorch.

### Measured caveat — this dataset leaks its labels

The Kaggle classes differ in *how they were produced*, not only in whether they are
forged. Measured on the 277 usable images with a width/height/file-size logistic
regression (5-fold ROC-AUC):

| Pipeline | width/height/bytes | bytes only | width/height only |
|---|---|---|---|
| Raw files | 0.966 | 0.969 | 0.966 |
| + size normalised (short side 384) | 0.889 | 0.647 | 0.842 |
| + orientation normalised (portrait) | **0.629** | 0.640 | 0.644 |

Raw files: real certificates are median **1190x1683 / 278 KB**, fakes **256x197 / 8 KB**.
Real certificates are portrait 87% of the time, fakes only 19%.

The notebook normalises size **and** orientation before training, which drops the
shortcut from 0.966 to 0.629 — near chance. `metadata_only_roc_auc_normalised` in
`certificate_metrics.json` records the number that matters. Because 277 images is
still tiny, the CNN remains a **secondary signal only** and must never flip a verdict.

See `ml/data/README.md` for full dataset documentation.

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
