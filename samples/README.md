# HireShield-AI — Sample Test Opportunity Files

This directory contains ready-to-use sample opportunity files representing different risk categories. You can test them via the Web UI at http://localhost:3000/analyze or via the REST API.

---

## Included Samples

| # | File Name | Category | Expected Verdict | Key Characteristics |
|---|---|---|---|---|
| **01** | `01_safe_stripe_internship.json` | Legitimate Enterprise | 🟢 `APPLY` (Score < 15) | Official corporate domain (`stripe.com`), corporate recruiter email, authentic terms. |
| **02** | `02_indian_consultancy_placement_scam.json` | Placement Fee Scam | 🔴 `DON'T APPLY` (Score > 85) | Demands ₹5,000 "refundable" security deposit, WhatsApp-only contact, `@gmail.com` recruiter. |
| **03** | `03_telegram_crypto_task_scam.json` | High-Yield Task Scam | 🔴 `DON'T APPLY` (Score > 85) | $1,500/week payout promise, anonymous Telegram handle (`@fast_crypto_jobs`), disposable `.site` TLD. |
| **04** | `04_counterfeit_offer_letter_cashier_check.json` | Cashier Check Fraud | 🔴 `DON'T APPLY` (Score > 85) | $2,000 hardware check reimbursement trap, lookalike domain (`apex-global-careers-hire.net`). |

---

## How to Test

### Method A: Web UI
1. Open http://localhost:3000/analyze.
2. Click on any of the **1-Click Test Presets** at the top of the form, or copy-paste text from the `.txt` / `.json` files.
3. Click **"Run Comprehensive Safety Assessment"**.

### Method B: cURL / REST API
```bash
curl -X POST http://127.0.0.1:8000/api/v1/assessments \
  -H "Content-Type: application/json" \
  -d @samples/02_indian_consultancy_placement_scam.json
```

### Method C: Python Script
```python
import requests

with open("samples/02_indian_consultancy_placement_scam.json") as f:
    data = f.read()

resp = requests.post(
    "http://127.0.0.1:8000/api/v1/assessments",
    headers={"Content-Type": "application/json"},
    data=data,
)
print(resp.json())
```
