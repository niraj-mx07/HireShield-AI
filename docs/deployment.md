# HireShield-AI — Production Deployment Guide

This guide details the recommended production deployment paths for **HireShield-AI**.

---

## 🏆 Recommended: Split Cloud Deployment (Vercel + Render + MongoDB Atlas)

This provides **zero-maintenance**, **instant global edge delivery**, and **automatic scaling**:

| Component | Platform | Plan | Purpose |
|---|---|---|---|
| **Frontend** | [Vercel](https://vercel.com) | Free | Global Edge CDN, instant Vite React delivery, zero-config SSL. |
| **Backend API** | [Render](https://render.com) | Free | Docker container with FastAPI, loaded ML models, and cached DNS. |
| **Database** | [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) | Free | High-availability cloud MongoDB with automatic indexes and user auth persistence. |

---

### Step 1: Database (MongoDB Atlas)
1. Log in to [MongoDB Atlas](https://cloud.mongodb.com) and create a free M0 cluster (e.g. AWS / us-east-1).
2. Go to **Database Access** -> Add new Database User (username & password).
3. Go to **Network Access** -> Add IP Address: `0.0.0.0/0` (allow access from cloud providers).
4. Go to **Clusters** -> Click **Connect** -> **Drivers** -> Copy the connection string:
   ```text
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/hireshield?retryWrites=true&w=majority
   ```

---

### Step 2: Backend API (Render via Docker / Blueprint)

HireShield-AI includes a pre-configured [render.yaml](../render.yaml) blueprint!

#### Option A: 1-Click Render Blueprint (Fastest)
1. Sign in to [Render](https://dashboard.render.com).
2. Click **New +** -> **Blueprint**.
3. Connect your repository: `https://github.com/niraj-mx07/HireShield-AI`.
4. Select the branch: `Deep-trying`.
5. Render reads `render.yaml` automatically:
   * Prompts for `DATABASE_URL`: Paste your MongoDB Atlas URI from Step 1.
6. Click **Apply**.
7. Render will build the container using `backend/Dockerfile` and give you an API URL (e.g., `https://hireshield-api.onrender.com`).

#### Option B: Manual Web Service Setup
1. On Render, click **New +** -> **Web Service**.
2. Select your repository: `HireShield-AI` (Branch: `Deep-trying`).
3. Set **Runtime**: `Docker`.
4. Set **Dockerfile Path**: `backend/Dockerfile`.
5. Set **Docker Context**: `.` (Repository root).
6. Under **Environment Variables**, add:
   * `DATABASE_URL`: `<your-mongodb-atlas-uri>`
   * `DATABASE_NAME`: `hireshield`
   * `CORS_ORIGINS`: `*`
   * `SECRET_KEY`: `<any-random-32-character-secret>`
   * `LOG_LEVEL`: `INFO`
7. Set **Health Check Path**: `/health`.
8. Click **Deploy Web Service**.

---

### Step 3: Frontend (Vercel)

1. Sign in to [Vercel](https://vercel.com).
2. Click **Add New...** -> **Project** -> Import `HireShield-AI`.
3. In the project settings:
   * **Framework Preset**: `Vite`
   * **Root Directory**: Click *Edit* and select `frontend`.
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
4. Expand **Environment Variables** and add:
   * `VITE_API_BASE_URL`: Your Render backend URL (e.g., `https://hireshield-api.onrender.com`)
   *(Ensure there is no trailing slash!)*
5. Click **Deploy**.
6. Vercel automatically reads `frontend/vercel.json` for client-side SPA routing (`/analyze`, `/dashboard`, `/history`).

---

## 🐳 Alternative: Self-Hosted Docker Compose (VPS / AWS EC2 / DigitalOcean)

To run the entire system on a single Linux server / droplet:

1. SSH into your VPS:
   ```bash
   git clone -b Deep-trying https://github.com/niraj-mx07/HireShield-AI.git
   cd HireShield-AI
   ```
2. Start the full stack in detached mode:
   ```bash
   docker compose up -d --build
   ```
3. View real-time container logs:
   ```bash
   docker compose logs -f
   ```
4. Access endpoints:
   * Web UI: `http://<your-server-ip>:3000`
   * API Documentation: `http://<your-server-ip>:8000/docs`
   * Health Check: `http://<your-server-ip>:8000/health`
