# HireShield-AI — Production Deployment Guide

This guide covers deployment options for **HireShield-AI** across modern cloud platforms.

---

## Architecture Overview

```
[User Browser]
      │
      ▼
[Frontend: React / Vite] ──(VITE_API_BASE_URL)──► [Backend: FastAPI Python 3.12]
                                                         │
                                                         ▼
                                                [Database: MongoDB]
                                                         │
                                                [ML Artifacts: TF-IDF + Logistic Regression]
```

---

## Option 1: Docker Compose (Full-Stack 1-Click Deployment)

### Prerequisites
* Docker Engine & Docker Compose installed.

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/niraj-mx07/HireShield-AI.git
   cd HireShield-AI
   ```
2. Run the full stack:
   ```bash
   docker-compose up --build -d
   ```
3. Access services:
   * **Frontend UI**: `http://localhost:3000`
   * **Backend API**: `http://localhost:8000`
   * **API Docs**: `http://localhost:8000/docs`

---

## Option 2: Split Cloud Deployment (Vercel + Render / Railway)

### 1. Database (MongoDB Atlas)
1. Create a free MongoDB Atlas cluster at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas).
2. Create a database user and whitelist network access (`0.0.0.0/0`).
3. Copy the Connection String URI: `mongodb+srv://<user>:<password>@cluster.mongodb.net/hireshield?retryWrites=true&w=majority`.

### 2. Backend (Render / Railway)
1. Connect your GitHub repository on Render/Railway.
2. Set Root Directory: `backend`
3. Environment: `Python 3.12`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Set Environment Variables:
   * `DATABASE_URL`: Your MongoDB Atlas Connection String
   * `DATABASE_NAME`: `hireshield`
   * `CORS_ORIGINS`: `https://your-frontend-domain.vercel.app`
   * `LOG_LEVEL`: `INFO`
7. Copy the generated backend service URL (e.g. `https://hireshield-api.onrender.com`).

### 3. Frontend (Vercel)
1. Connect the repository on [Vercel](https://vercel.com).
2. Set Root Directory: `frontend`
3. Framework Preset: `Vite`
4. Build Command: `npm run build`
5. Output Directory: `dist`
6. Add Environment Variable:
   * `VITE_API_BASE_URL`: `https://hireshield-api.onrender.com`
7. Click **Deploy**.

---

## Option 3: Testing Sample Datasets in Production

Pre-configured sample files are located in [`samples/`](../samples/):
```bash
# Test sample with production backend
curl -X POST https://your-backend.onrender.com/api/v1/assessments \
  -H "Content-Type: application/json" \
  -d @samples/02_indian_consultancy_placement_scam.json
```
