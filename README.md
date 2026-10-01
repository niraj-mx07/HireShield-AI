# HireShield-AI

[![Project Status](https://img.shields.io/badge/status-design%20phase-slateblue)](./README.md)
[![Domain](https://img.shields.io/badge/domain-job%20fraud%20detection-0f766e)](./README.md)
[![License](https://img.shields.io/badge/license-TBD-lightgrey)](./README.md)

HireShield-AI is an opportunity-credibility assessment system for students, freshers, and job seekers. It evaluates job and internship listings before application using hybrid AI/ML, NLP, rule-based risk detection, document inspection, URL/domain analysis, and independent public-web verification.

## Table of Contents

- [Problem](#problem)
- [Approach](#approach)
- [System Architecture](#system-architecture)
- [Pipeline Flow](#pipeline-flow)
- [Core Scoring and Intelligence Engine](#core-scoring-and-intelligence-engine)
- [Tech Stack](#tech-stack)
- [Datasets and Knowledge Bases](#datasets-and-knowledge-bases)
- [Output](#output)
- [Local Setup](#local-setup)
- [Developer Commands Cheatsheet](./COMMANDS.md)
- [Project Structure](#project-structure)
- [Privacy and Safety Design](#privacy-and-safety-design)
- [Team](#team)

## Problem

Job scams commonly imitate legitimate recruiting processes through cloned domains, unverified recruiter identities, advance-payment requests, urgency language, and inconsistent offer documents. Individual signals are weak in isolation: a real company may use a third-party job board, while a polished offer letter may still contain fraudulent payment clauses.

HireShield-AI aggregates these signals into an explainable risk assessment. It is designed to support a decision, not to establish legal fact or replace independent judgment.

## Approach

The system accepts a job/internship URL, pasted description, company or recruiter details, recruitment email/message, and uploaded offer letters or PDFs.

1. **Extraction** — Convert URL, text, and documents into structured entities such as company name, role title, compensation, location, recruiter email, contact details, and payment terms.
2. **AI/ML and NLP analysis** — Detect financial-scam indicators, urgency or pressure language, unrealistic promises, and recruitment-process red flags.
3. **URL and website analysis** — Inspect HTTPS, redirects, domain age/reputation where available, company-domain mismatches, and whether a source is an official site, a third-party platform, or suspicious.
4. **External verification** — Independently check company existence, official careers pages, job-posting presence, and recruiter identity against public sources.
5. **Document analysis** — Review offer letters and PDFs for consistency, formatting anomalies, payment clauses, and conflicts with verified public information.
6. **Risk scoring** — Aggregate weighted category scores into a normalized 0–100 risk score.
7. **Recommendation** — Produce `APPLY`, `HOLD`, or `DON'T APPLY` based on risk band, evidence coverage, and confidence.
8. **Explainable output** — Return each risk factor with severity, evidence, source status, and confidence level.

## System Architecture

```mermaid
graph LR
    U[User] --> FE[Frontend]
    FE --> API[Backend API]
    API --> NLP[NLP / ML Analysis]
    API --> URL[URL / Domain Analysis]
    API --> DOC[Document Analysis]
    NLP --> RISK[Risk Engine]
    URL --> RISK
    DOC --> RISK
    RISK --> VERIFY[Verification / Web Research]
    VERIFY --> EXPLAIN[Recommendation + Explanation Layer]
    RISK --> EXPLAIN
    EXPLAIN --> REPORT[Final Report]
```

## Pipeline Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as Backend API
    participant Analysis as NLP/URL/Document Analysis
    participant Verify as Web Verification
    participant Risk as Risk Engine
    participant Report as Explanation Layer

    User->>FE: Submit URL, text, details, or document
    FE->>API: Create assessment request
    API->>Analysis: Extract entities and evaluate signals
    Analysis-->>API: Findings and extracted fields
    API->>Verify: Verify company, posting, and recruiter
    Verify-->>API: Verification evidence / unavailable checks
    API->>Risk: Aggregate weighted signals
    Risk-->>API: Score, band, and confidence
    API->>Report: Build recommendation and explanations
    Report-->>FE: Final assessment report
    FE-->>User: Risk score and evidence breakdown
```

## External Verification and Entity Extraction

Two backend services implement the "verification via retrieval" capability. Both are consent-gated and exception-safe: a failure degrades the assessment instead of failing it.

| Service | Module | Behaviour |
| --- | --- | --- |
| Public page retrieval | `app/services/web_retrieval.py` | Fetches the submitted listing URL (HTML only, size- and timeout-capped), rejects non-HTTP(S) schemes, and blocks loopback/private/link-local/metadata hosts (SSRF guard). Parses the title, meta description, visible text, outbound link domains, `JobPosting` JSON-LD, apply/resume forms, and payment keywords. Falls back to a dependency-free regex parser when `beautifulsoup4` is unavailable. |
| Named-entity extraction | `app/services/nlp_entities.py` | Two layers: (1) deterministic regex identifiers (email, URL, phone, UPI, crypto wallet, money) and (2) contextual NER resolved as spaCy → Hugging Face Transformers → regex-only. Canonical labels include `PERSON`, `ORG`, `LOCATION`, `DATE`, `MONEY`, `EMAIL`, `PHONE`, `URL`, `UPI_ID`, `CRYPTO_WALLET`. |

The pipeline performs **one** page fetch per assessment when `consent_for_external_lookups=true` and retrieval is enabled, then shares the parsed page with the job-content analyzer (page text as an extra ML input) and the company-verification analyzer (live payment-prompt, job-posting, and apply-form signals). Trusted job boards are never re-fetched because they already host the listing. Extracted entities are returned to the caller in `AssessmentResponse.entities` and are never persisted.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `WEB_RETRIEVAL_ENABLED` | `true` | Master switch for external page retrieval. |
| `WEB_RETRIEVAL_TIMEOUT` | `6.0` | Per-request timeout in seconds. |
| `WEB_RETRIEVAL_MAX_BYTES` | `524288` | Response size cap (512 KB). |
| `NLP_NER_ENABLED` | `true` | Enable contextual NER; regex identifiers always run. |
| `TRANSFORMERS_NER_ENABLED` | `true` | Allow the Hugging Face fallback when spaCy is unavailable. |
| `SPACY_MODEL` | `en_core_web_sm` | spaCy pipeline used for NER. |
| `TRANSFORMERS_NER_MODEL` | `dslim/bert-base-NER` | Token-classification model for the Transformer fallback. |

## Core Scoring and Intelligence Engine

HireShield-AI uses a hybrid detector: ML prediction, deterministic rules, URL analysis, company/recruiter verification, document analysis, and cross-source information consistency are combined in a single Risk Engine. Model output is one signal among several; it does not override high-severity evidence such as advance-payment demands or a verified domain mismatch.

| Category | Weight | Example signals |
| --- | ---: | --- |
| Job Content Analysis | 20% | Vague role scope, unrealistic salary, missing employer details |
| Company Verification | 20% | Company/careers-page presence, public business footprint, posting match |
| Recruiter Verification | 15% | Email-domain match, public professional identity, contact consistency |
| URL/Website Analysis | 15% | HTTPS, redirects, official-domain match, platform classification |
| Financial/Scam Signals | 15% | Registration fees, deposits, payment requests, urgency language |
| Document Analysis | 10% | Offer-letter structure, payment clauses, logo/contact anomalies |
| Information Consistency | 5% | Conflicts across listing, email, document, and public sources |

| Risk score | Risk band | Default recommendation |
| ---: | --- | --- |
| 0–30 | Low | 🟢 APPLY |
| 31–60 | Moderate | 🟡 HOLD |
| 61–80 | High | 🔴 DON'T APPLY |
| 81–100 | Very High | 🔴 DON'T APPLY |

Thresholds are policy configuration, not fixed truth. Missing evidence reduces confidence and can result in `HOLD` even when the score is below a rejection threshold.

## Tech Stack

The table below reflects the implemented stack; optional extras are marked and can be omitted from a minimal install.

| Layer | Intended technology | Responsibility |
| --- | --- | --- |
| Frontend | React | Submission workflow, report visualization, explanations |
| Backend API | FastAPI or Node.js | Assessment orchestration and API endpoints |
| Database | MongoDB or PostgreSQL | Assessments, extracted entities, evidence, audit metadata |
| ML models | Logistic Regression, Random Forest, SVM; transformer classifier as stretch goal | Baseline and advanced job-scam classification |
| NLP | spaCy (`en_core_web_sm`); optional Hugging Face Transformers | Entity extraction (regex identifiers + contextual NER), text classification, signal detection |
| Verification | `requests` + BeautifulSoup (stdlib regex fallback) | Public-page retrieval and structured verification checks |
| Deployment | Vercel (frontend), Render or Railway (backend) | Managed web deployment |

## Datasets and Knowledge Bases

| Source | Use in the system | Notes |
| --- | --- | --- |
| Kaggle — “Real or Fake Job Posting” dataset | Supervised baseline training and evaluation | Validate labels, class balance, licensing, and feature leakage before use |
| Official company websites and careers pages | Company and posting verification | Treat unavailable pages as unknown, not fraudulent |
| Public professional/company directories | Recruiter and company corroboration | Evidence only; respect site terms and rate limits |
| URL/domain metadata sources | Domain and redirect risk checks | Keep source and retrieval time with each result |
| Curated scam-pattern rules | Payment, impersonation, urgency, and contact-pattern detection | Version rules and retain matching evidence |

## Output

Each assessment returns:

- A **risk score** from 0–100.
- A recommendation: **🟢 APPLY**, **🟡 HOLD**, or **🔴 DON'T APPLY**.
- An explainable risk-factor breakdown by category and severity: **🔴 High**, **🟠 Medium**, or **🟢 Low**.
- A confidence level reflecting evidence completeness and signal agreement.
- Verification evidence marked **✓ verified** or **⚠ unable to verify**, with the associated source/check.

## Local Setup

The commands below define the expected development workflow once the application scaffold exists. Replace placeholder values and package commands if the final implementation differs.

### 1. Clone

```bash
git clone https://github.com/niraj-mx07/HireShield-AI.git
cd HireShield-AI
```

### 2. Configure and install the backend

```bash
cd backend
cp .env.example .env
# Set DATABASE_URL, CORS_ORIGINS, and any verification-provider credentials in .env
pip install -r requirements.txt

# Optional: contextual NLP entity extraction (spaCy model + optional Transformers).
# The API runs without these — NER degrades to regex identifiers, and
# WEB_RETRIEVAL_ENABLED / NLP_NER_ENABLED can disable the features entirely.
pip install -r requirements-nlp.txt
```

### 3. Configure and install the frontend

```bash
cd ../frontend
cp .env.example .env
# Set the backend API base URL, for example VITE_API_BASE_URL
npm install
```

### 4. Run locally

Run these from separate terminals:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev
```

> **Detailed Command Reference**: See [`COMMANDS.md`](./COMMANDS.md) for full ML training, testing, Docker, and troubleshooting commands.

## Project Structure

Below is the current repository layout (code-only; build outputs, virtual environments, and raw datasets are git-ignored).

```text
HireShield-AI/
├── README.md
├── COMMANDS.md                 # Developer command cheatsheet
├── docker-compose.yml          # Full-stack orchestration (frontend + backend + MongoDB)
├── backend/                    # FastAPI service
│   ├── app/
│   │   ├── api/                # /api/v1 routes
│   │   ├── analyzers/          # 7 category risk analyzers
│   │   ├── models/             # Pydantic schemas
│   │   ├── services/           # pipeline, risk engine, ML loader, web retrieval, NER
│   │   ├── utils/              # privacy/redaction helpers
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── samples/                # Sample API request payloads (.json)
│   ├── scripts/                # DB migrate & seed
│   ├── tests/                  # pytest suite
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-nlp.txt    # Optional spaCy / Transformers NER providers
│   └── .env.example
├── frontend/                   # React + Vite SPA
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── data/
│   │   ├── pages/
│   │   └── services/
│   ├── Dockerfile
│   ├── nginx.conf              # Production web-server config
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── vite.config.js
│   └── .env.example
├── ml/                         # Training & evaluation pipeline
│   ├── training/               # download_data, preprocess, feature_extractor, train_*
│   ├── evaluation/             # evaluate.py, eda_analysis.py, metrics.json, plots/
│   ├── artifacts/              # Trained model + TF-IDF vectoriser (.joblib)
│   ├── data/                   # raw/ + processed/ (git-ignored)
│   ├── requirements.txt
│   ├── README.md
│   └── .env.example
└── docs/
    ├── deployment.md
    └── frontend/               # Frontend design & component docs
```

## Privacy and Safety Design

- Treat uploaded offers, email addresses, phone numbers, and recruiter details as sensitive data.
- Minimize collection and retain raw inputs only as long as required for the assessment and user-visible history.
- Encrypt data in transit and at rest; restrict document access to the submitting user and authorized service components.
- Redact or hash personal identifiers in logs, analytics, training data, and error reports.
- Record evidence provenance, retrieval time, and rule/model version for auditability.
- Do not make unqualified claims that a company or person is fraudulent. Present risk indicators, verification limits, and supporting evidence.
- Require explicit user action before external lookups when submitted content may contain personal information.
- Extracted entities are returned to the caller only and are never written to the assessment record; the pipeline performs at most one consent-gated page retrieval per assessment.
- External retrieval is restricted to public HTTP(S) hosts — a failed or blocked fetch is reported as *unavailable*, never as evidence of fraud.

## Team

| Member | Role |
|---|---|
| Nihar Patil | Project Lead / Front-end Development |
| Niraj Mahajan| ML and NLP Engineering |
| Vansh Ahire | Data Collection, Testing, and Documentation |
| Deep Patil | Backend Development and Database |

