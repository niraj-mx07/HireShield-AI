# Dataset: Real or Fake Job Posting

## Source

**Kaggle:** [Real or Fake — Fake Job Posting Prediction](https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction)

**Author:** Shivam Bansal

## Description

~17,880 job postings with 17 feature columns and a binary `fraudulent` label
(0 = real, 1 = fraudulent). The dataset was assembled to support research on
job-scam detection.

## Known characteristics

| Property | Value |
|---|---|
| Total rows | ~17,880 |
| Fraudulent (label=1) | ~866 (~4.8 %) |
| Real (label=0) | ~17,014 (~95.2 %) |
| Class imbalance ratio | ~20:1 |

The dataset is **heavily imbalanced** — accuracy alone is a misleading metric.
Evaluation must use precision, recall, and F1 (especially for the minority
fraudulent class).

## Licensing

The dataset is published on Kaggle under the
[CC0: Public Domain](https://creativecommons.org/publicdomain/zero/1.0/) license.
It may be used for any purpose without restriction.

## Feature leakage notes

- No column trivially encodes the label (confirmed by the validation script).
- The `fraudulent` column is the only target — all other columns are
  legitimate input features.
- Some text fields (e.g., `company_profile`) have high missing rates; the
  *absence* of a company profile correlates with fraud but is a legitimate
  signal, not leakage.

## File layout

```
ml/data/
├── raw/
│   └── fake_job_postings.csv   ← downloaded or manually placed here
└── README.md                   ← this file
```
