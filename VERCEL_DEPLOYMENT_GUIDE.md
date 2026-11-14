# ASTRA SENSE – ORBITAL GUARD
# VERCEL DEPLOYMENT GUIDE

**Project:** ASTRA SENSE – ORBITAL GUARD  
**Repository:** `https://github.com/Sarthakadhav/ASTRA-SENSE-ORBITAL-GUARD.git`  
**Architecture:** React 19 + Vite 6 Frontend (Static SPA) + FastAPI Serverless Backend (`api/index.py`) + Supabase PostgreSQL Cloud Replication  

---

## 1. Overview of Vercel Configuration

The repository is configured for full-stack deployment on Vercel:
- **Frontend SPA:** Compiled with Vite 6 into `dist/`.
- **Backend API:** FastAPI application routed through Vercel Python Serverless Function (`api/index.py`).
- **Routing:** Handled via `vercel.json`:
  - `/api/(.*)` -> `/api/index.py` (FastAPI endpoints)
  - `/docs` & `/openapi.json` -> `/api/index.py` (Interactive Swagger documentation)
  - `/(.*)` -> `/index.html` (React client-side routing)
- **Database on Vercel:** Automated `/tmp/orbital_guard.db` initialization on serverless cold starts.

---

## 2. Deploying via Vercel Web Dashboard (Recommended)

### Step 1: Import GitHub Repository
1. Log in to [vercel.com](https://vercel.com).
2. Click **Add New...** > **Project**.
3. Under **Import Git Repository**, select **`Sarthakadhav/ASTRA-SENSE-ORBITAL-GUARD`**.

### Step 2: Configure Project Settings
- **Framework Preset:** Vite
- **Root Directory:** `./` (leave default)
- **Build Command:** `npm run build`
- **Output Directory:** `dist`

### Step 3: Add Environment Variables
In the **Environment Variables** section of the Vercel project configuration, add:

| Variable Name | Example / Description |
| :--- | :--- |
| `ENVIRONMENT` | `flight_simulation` |
| `DEBUG` | `False` |
| `SUPABASE_URL` | `https://kgjbltqunjpscyipwgll.supabase.co` |
| `SUPABASE_SECRET_KEY` | `sb_secret_your_supabase_secret_key` |
| `SUPABASE_PUBLISHABLE_KEY`| `your_supabase_publishable_anon_key` |
| `SUPABASE_SYNC_ENABLED` | `True` |

> [!IMPORTANT]
> Never commit actual secret keys to Git. Enter them directly into the Vercel Project Settings > Environment Variables console.

### Step 4: Click Deploy
Click **Deploy**. Vercel will:
1. Clone the repository.
2. Install Node.js dependencies (`npm install`) and build the Vite frontend (`npm run build`).
3. Install Python dependencies from `api/requirements.txt`.
4. Deploy the frontend assets to Vercel Global Edge Network and the backend to Vercel Serverless Functions.

---

## 3. Deploying via Vercel CLI (Alternative)

If you have the Vercel CLI or the Vercel Plugin installed:

```bash
# 1. Log in to Vercel
npx vercel login

# 2. Deploy preview build
npx vercel

# 3. Deploy to production
npx vercel --prod
```

---

## 4. Post-Deployment Verification

Once deployed, your Vercel deployment URL (e.g. `https://astra-sense-orbital-guard.vercel.app`) provides:
1. **Interactive Mission Dashboard:** `https://<your-project>.vercel.app/`
2. **FastAPI Health & Status:** `https://<your-project>.vercel.app/api/v1/system/status`
3. **Interactive API Documentation:** `https://<your-project>.vercel.app/docs`
4. **Cloud Synchronization Center:** Module 8 tab for live Supabase status, outbox backlog, and health metrics.
