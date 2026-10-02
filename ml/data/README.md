# Datasets & Sources: Job Scam Detection

HireShield-AI combines multiple datasets covering global postings, Indian job consultancy scams, and fake contract/internship offers.

## Sources

### 1. Kaggle — Real or Fake Job Posting Prediction
- **Author / Link:** [Shivam Bansal](https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction)
- **Rows:** ~17,880 postings
- **License:** CC0 (Public Domain)
- **Scope:** Global fake job postings across industries.

### 2. Kaggle — Indian Job Fraud Dataset
- **Author / Link:** [Adit Sawhney](https://www.kaggle.com/datasets/aditsawhney/indian-job-fraud-dataset)
- **File:** `synthetic_indian_jobs.csv` (~752 rows)
- **License:** CC0-1.0
- **Scope:** Real-world Indian hiring scams (security deposits, registration charges, WhatsApp contacts, fake MNC interviews).

### 3. Kaggle — Detecting Fake Job Postings and Internship Scams
- **Author / Link:** [Sohaib Dev](https://www.kaggle.com/datasets/sohaibdevv/detecting-fake-job-postings-and-internship-scams)
- **File:** `job_contract_scam_dataset.csv` (~1,000 rows)
- **License:** Apache-2.0
- **Scope:** Fake internship contracts, equipment shipping scams, and withholding bond agreements.

### 4. Curated India Scam Signatures
- **File:** `india_job_scams.json`

### 5. Kaggle — Internship Certificates (image dataset)
- **Author / Link:** [godzilla04](https://www.kaggle.com/datasets/godzilla04/internship-certificates)
- **Files:** 287 images (~104 MB) — 165 `Real internship certificate`, 122 `fake internship certificate`
- **License:** CC0: Public Domain
- **Scope:** Genuine vs. forged internship certificate scans, used to train the
  certificate forgery CNN (`ml/notebooks/train_certificate_cnn.ipynb`).
- **Measured caveat:** the two classes are not comparable in build quality. Real
  certificates are median **1190x1683 / 278 KB** and portrait 87% of the time; fakes
  are median **256x197 / 8 KB** and portrait only 19%. A logistic regression on
  width/height/file size alone scores **ROC-AUC 0.966** — i.e. the label is readable
  from the file metadata. The training notebook therefore rescales every image to a
  common short side (384) *and* rotates landscape scans upright, which lowers that
  baseline to **0.629**. Treat any score from this model as a weak, secondary signal.
- **Handling:** images stay in `ml/data/raw/certificates/` (git-ignored); only the
  stratified split index and `summary.json` are written to
  `ml/data/processed/certificates/`. Prepare with:
  `python -m ml.training.download_certificates`.

## Combined Statistics

| Property | Value |
|---|---|
| Total raw entries across sources | ~19,650 |
| After deduplication (exact + near-duplicate) | ~16,827 unique postings |
| Train set (80%) | 13,461 postings (6.5% fraud) |
| Test set (20%) | 3,366 postings (6.5% fraud) |

## File layout

```
ml/data/
├── raw/
│   ├── fake_job_postings.csv
│   ├── synthetic_indian_jobs.csv
│   ├── job_contract_scam_dataset.csv
│   └── india_job_scams.json
├── processed/
│   ├── train.csv
│   └── test.csv
└── README.md
```
