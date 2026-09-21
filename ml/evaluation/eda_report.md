# Exploratory Data Analysis (EDA) Report — HireShield-AI

## 1. Executive Summary
- **Total Training Records**: 13,461 job postings
- **Total Test Records**: 3,366 job postings
- **Fraud Class Proportion**: 6.47% (871 positive instances)
- **Imbalance Ratio**: ~14.5:1 (Legitimate : Fraudulent)

## 2. Raw Source Breakdown

| Source | File | Rows | Fraudulent Rows | Fraud Rate |
|---|---|---|---|---|
| Kaggle Global | `fake_job_postings.csv` | 17,880 | 866 | 4.8% |
| Indian Job Fraud | `synthetic_indian_jobs.csv` | 752 | 300 | 39.9% |
| Contract / Internship Scams | `job_contract_scam_dataset.csv` | 1,000 | 93 | 9.3% |
| India Scam Signatures | `india_job_scams.json` | 18 | 10 | 55.6% |

## 3. Structural & Linguistic Comparison

| Metric | Legitimate Postings (0) | Fraudulent Postings (1) | Fraud Delta / Pattern |
|---|---|---|---|
| Mean Word Count | 386.3 words | 228.9 words | Shorter / concise fake ads |
| Mean Character Count | 2740.7 chars | 1669.5 chars | Characteristic length signature |
| Uppercase Character Ratio | 3.60% | 4.60% | High emphasis / capitalization in scams |
| Digit Character Ratio | 1.40% | 3.00% | Phone numbers & salary amounts |
| Exclamation Marks Avg | 0.66 | 0.53 | High urgency punctuation in scams |

## 4. Top Discriminative Fraud Terms (TF-IDF Association)

| Rank | Keyword / N-Gram | Association Score | Fraud TF-IDF Avg | Real TF-IDF Avg |
|---|---|---|---|---|
| 1 | **000** | 0.0626 | 0.0678 | 0.0052 |
| 2 | **000 month** | 0.0403 | 0.0412 | 0.0009 |
| 3 | **data entry** | 0.0316 | 0.0328 | 0.0012 |
| 4 | **month** | 0.0278 | 0.0320 | 0.0043 |
| 5 | **entry** | 0.0255 | 0.0290 | 0.0035 |
| 6 | **earn** | 0.0250 | 0.0261 | 0.0011 |
| 7 | **freshers** | 0.0197 | 0.0198 | 0.0000 |
| 8 | **fee** | 0.0167 | 0.0172 | 0.0005 |
| 9 | **com** | 0.0159 | 0.0177 | 0.0018 |
| 10 | **25 000** | 0.0158 | 0.0160 | 0.0002 |
| 11 | **50 000** | 0.0152 | 0.0158 | 0.0006 |
| 12 | **guaranteed** | 0.0143 | 0.0148 | 0.0005 |
| 13 | **home** | 0.0143 | 0.0230 | 0.0087 |
| 14 | **good communication** | 0.0139 | 0.0150 | 0.0011 |
| 15 | **500** | 0.0139 | 0.0167 | 0.0028 |

## 5. Key Findings for Performance Boosting

1. **Class Imbalance**: Severe ~14.4:1 imbalance. Standard 0.5 threshold suppresses Recall. Threshold tuning + balanced class weights are essential.
2. **Informal Channels & Contact Obfuscation**: Fraudulent postings frequently embed WhatsApp, Telegram, or Gmail handles rather than standard corporate ATS links.
3. **Indian Scam Signatures**: High concentration of payment fees ('registration fee', 'refundable deposit', 'bond agreement') and low-barrier high-pay promises ('data entry', 'form filling').
4. **Character & Subword Patterns**: Obfuscated terms benefit strongly from combining Word TF-IDF + Character n-grams (3-5) with explicit engineered domain heuristics.

