# HireShield-AI — Sample Test Opportunity Files

This directory contains ready-to-use sample opportunity files representing different risk categories. You can test them via the Web UI at http://localhost:5173/analyze or via the FastAPI REST API.

---

## Included Test Samples

| # | File Name | Category | Expected Verdict | Key Characteristics |
|---|---|---|---|---|
| **01** | `01_safe_stripe_internship.json` | Legitimate Enterprise | 🟢 `APPLY` (Score < 15) | Official corporate domain (`stripe.com`), corporate recruiter email, authentic terms. |
| **02** | `02_indian_consultancy_placement_scam.json` | Placement Fee Scam | 🔴 `DON'T APPLY` (Score > 85) | Demands ₹5,000 "refundable" security deposit, WhatsApp-only contact, `@gmail.com` recruiter. |
| **03** | `03_telegram_crypto_task_scam.json` | High-Yield Task Scam | 🔴 `DON'T APPLY` (Score > 85) | $1,500/week payout promise, anonymous Telegram handle (`@fast_crypto_jobs`), disposable `.site` TLD. |
| **04** | `04_counterfeit_offer_letter_cashier_check.json` | Cashier Check Fraud | 🔴 `DON'T APPLY` (Score > 85) | $2,000 hardware check reimbursement trap, lookalike domain (`apex-global-careers-hire.net`). |
| **05** | `05_check_reimbursement_fastpay_scam.json` | Equipment Reimbursement Scam | 🔴 `DON'T APPLY` (Score > 85) | Fake $3,500 equipment cashier's check, $450 Zelle fee demand, disposable `.xyz` TLD. |
| **06** | `06_tcs_rfid_gatepass_placement_scam.json` | Indian Placement Fee Scam | 🔴 `DON'T APPLY` (Score > 85) | TCS impersonation, ₹2,450 RFID Gate Pass fee, personal UPI (`@okaxis`), `@gmail.com` recruiter. |
| **07** | `07_telegram_youtube_rating_crypto_scam.json` | Telegram Task & Crypto Scam | 🔴 `DON'T APPLY` (Score > 85) | YouTube rating tasks, Telegram coordinator `@Elena_JobHR`, ₹2,000 VIP arbitrage upgrade trap. |
| **08** | `08_verified_google_software_engineer.json` | Verified Tech Enterprise | 🟢 `APPLY` (Score < 15) | Official career portal (`careers.google.com`), legitimate requirements, zero fee notice. |

---

## How to Test

### Method A: Web UI
1. Open http://localhost:5173/analyze in your browser.
2. Copy the fields from any `.json` sample file into the corresponding form inputs:
   - **Job URL**
   - **Job Description**
   - **Company Name**
   - **Recruiter Details (Email, Name, Phone)**
   - **Recruiter Message**
3. Click **"Run Comprehensive Safety Assessment"**.

### Method B: cURL / REST API
```bash
curl -X POST http://127.0.0.1:8000/api/v1/assessments \
  -H "Content-Type: application/json" \
  -d @samples/05_check_reimbursement_fastpay_scam.json
```

### Method C: Python Script
```python
import requests
import json

with open("samples/06_tcs_rfid_gatepass_placement_scam.json") as f:
    payload = json.load(f)

response = requests.post(
    "http://127.0.0.1:8000/api/v1/assessments",
    json=payload,
)
print("Risk Score:", response.json().get("risk_score"))
print("Recommendation:", response.json().get("recommendation"))
```
