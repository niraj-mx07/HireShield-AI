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
