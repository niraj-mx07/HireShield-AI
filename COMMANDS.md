# HireShield-AI — Developer Command Cheatsheet

A quick-reference guide for running, training, testing, and developing across the **HireShield-AI** full-stack repository.

---

## Table of Contents
1. [Quick Start (Run Everything)](#1-quick-start-run-everything)
2. [Backend (FastAPI)](#2-backend-fastapi)
3. [Frontend (React + Vite)](#3-frontend-react--vite)
4. [Machine Learning Pipeline](#4-machine-learning-pipeline)
5. [Docker Compose](#5-docker-compose)
6. [Troubleshooting & FAQs](#6-troubleshooting--faqs)

---

## 1. Quick Start (Run Everything)

To run the complete system locally, open two separate terminal windows:

### Terminal 1: Backend API
```powershell
cd c:\Users\new\HireShield-AI\backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
> API runs at: **http://127.0.0.1:8000**  
> Swagger Documentation: **http://127.0.0.1:8000/docs**  
> Health Check: **http://127.0.0.1:8000/health**

### Terminal 2: Frontend
```powershell
cd c:\Users\new\HireShield-AI\frontend
npm run dev
```
> Web UI runs at: **http://localhost:3000**

---

## 2. Backend (FastAPI)

All backend commands are run from the `backend/` folder:

```powershell
cd c:\Users\new\HireShield-AI\backend
```

### Install Dependencies
```powershell
# Base requirements (FastAPI, MongoDB, ML artifacts, BeautifulSoup, pypdf)
pip install -r requirements.txt

# Optional: contextual NLP entity extraction (spaCy + en_core_web_sm wheel).
# Skip this and the NER service still works using regex identifiers only.
pip install -r requirements-nlp.txt

# Equivalent manual install (if the wheel URL in requirements-nlp.txt is stale)
pip install spacy
python -m spacy download en_core_web_sm
```

### External Verification & NLP Toggles
`backend/app/services/web_retrieval.py` (public page retrieval) and
`backend/app/services/nlp_entities.py` (regex + NER entity extraction) both read
their switches from `.env` and degrade gracefully when disabled:

```dotenv
# .env
WEB_RETRIEVAL_ENABLED=true      # master switch for external page retrieval
WEB_RETRIEVAL_TIMEOUT=6.0       # per-request timeout (seconds)
WEB_RETRIEVAL_MAX_BYTES=524288  # response size cap (512 KB)
NLP_NER_ENABLED=true            # contextual NER (regex identifiers always run)
TRANSFORMERS_NER_ENABLED=true   # allow Hugging Face fallback if spaCy is absent
SPACY_MODEL=en_core_web_sm
TRANSFORMERS_NER_MODEL=dslim/bert-base-NER
```

Smoke-test that the spaCy provider is actually loaded (prints the model status
and a sample extraction):

```powershell
python -c "from app.services import nlp_entities as n; print(n._load_spacy() is not None); print([(e.label, e.text) for e in n.extract_entities('Ravi Kumar works at Acme Corporation in Bengaluru.').entities])"
```

> Entity extraction requires `consent_for_external_lookups=true` **only** for page
> retrieval; text you submit is analysed locally regardless. Retrieved entities are
> returned in the API response and never persisted.


### Start Backend Development Server
```powershell
# Default port 8000 with hot-reload
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Run on an alternate port if 8000 is occupied
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### Run from Root Directory
```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```

### Restart the Backend After Installing Dependencies or Swapping Models

> **Do this whenever you `pip install` anything, retrain a model, or replace a
> file in `ml/artifacts/`.** A running server keeps the interpreter state it was
> started with, so it will **not** see the new package or model and will keep
> serving results computed the old way — silently, with no error.

This is not hypothetical. A stale server started before `python-docx` was
installed kept decoding `.docx` uploads as raw bytes, so the extracted "text"
was binary noise. The document analyzer then mined a company name out of that
noise and reported a confident, completely fictional employer.

```powershell
# 1. Find what is holding port 8000
ss -tlnp | grep :8000

# 2. Stop it (use the PID from the output above)
kill <PID>

# 3. Start it again
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Confirm the new process is the one answering:

```powershell
curl -s http://127.0.0.1:8000/health
```

> **Why `--reload` is not enough:** it watches your *source files*, not
> `site-packages` or `ml/artifacts/`. Installing a dependency or replacing a
> model requires a full restart either way.
>
> **Checkpoints that are worth verifying after a restart:** the health endpoint
> responds, and `grep "Certificate CNN loaded" uvicorn.log` shows the model was
> picked up. A silent skip there means the artifact is missing, not that the
> analysis succeeded.

### Run Tests
```powershell
# Run all backend tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test suite
pytest tests/test_job_content_analyzer.py
pytest tests/test_risk_engine.py

# New feature suites: page retrieval, NLP entities, pipeline wiring
pytest tests/test_web_retrieval.py
pytest tests/test_nlp_entities.py
pytest tests/test_pipeline_entities.py
```

---

## 3. Frontend (React + Vite)

All frontend commands are run from the `frontend/` folder:

```powershell
cd c:\Users\new\HireShield-AI\frontend
```

### Install Dependencies
```powershell
npm install
```

### Start Local Development Server
```powershell
npm run dev
```

### Build for Production
```powershell
npm run build
```

### Preview Production Build
```powershell
npm run preview
```

---

## 4. Machine Learning Pipeline

All ML commands are run from the repository root (`c:\Users\new\HireShield-AI`):

```powershell
cd c:\Users\new\HireShield-AI
```

### 1. Download & Verify Datasets
Downloads the Real/Fake Job Postings dataset into `ml/data/raw/`:
```powershell
python -m ml.training.download_data
```

### 2. Preprocess & Split Data
Cleans HTML tags, combines features, and creates stratified 80/20 train and test sets in `ml/data/processed/`:
```powershell
python -m ml.training.preprocess
```

### 3. Train Model
Trains the classifiers, extracts TF-IDF n-grams + heuristic features, evaluates metrics, and outputs artifacts:
```powershell
# Train boosted model (TF-IDF + heuristic risk signals + soft-voting ensemble)
python -u -m ml.training.train_boosted

# Train baseline models (standard TF-IDF + Logistic Regression & Random Forest)
python -m ml.training.train_baseline
```

### Output Artifacts
* Trained Model: `ml/artifacts/best_model.joblib`
* TF-IDF Vectorizer: `ml/artifacts/tfidf_vectorizer.joblib`
* Metrics & Benchmark: `ml/evaluation/metrics.json`
* Comparison Plots: `ml/evaluation/plots/`

---

## 5. Docker Compose

Run the entire application stack (Frontend, Backend, and MongoDB) via Docker:

```powershell
# Start all services in the background
docker compose up -d

# View real-time logs
docker compose logs -f

# Stop all containers
docker compose down
```

---

## 6. Troubleshooting & FAQs

### Port Conflict `[WinError 10013]` / Port 8000 in use
If you get `An attempt was made to access a socket in a way forbidden by its access permissions`, another process is already listening on port 8000.

**Find and terminate the process holding port 8000 (PowerShell):**
```powershell
# Find PID
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object OwningProcess

# Stop process by PID (replace 1234 with actual PID)
Stop-Process -Id 1234 -Force
```

Or simply run uvicorn on an alternate port:
```powershell
uvicorn app.main:app --reload --port 8001
```
*(Remember to adjust `VITE_API_BASE_URL=http://127.0.0.1:8001` in `frontend/.env` if changing the backend port)*.

### MongoDB Connection Warning
The assessment engine runs standalone with in-memory rules and ML inference. If MongoDB is not running locally, database history persistence is skipped gracefully without interrupting analysis.
To start MongoDB locally with Docker:
```powershell
docker run -d -p 27017:27017 --name hireshield-mongo mongo:4.4   # 4.4 = last release that runs without CPU AVX support
```
