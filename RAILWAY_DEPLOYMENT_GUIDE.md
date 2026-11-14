# ASTRA SENSE – ORBITAL GUARD
# Complete Railway Single-Service Production Deployment Guide

## 1. Executive Summary & Architecture Overview

ASTRA SENSE – ORBITAL GUARD is deployed to Railway as **ONE combined application service with ONE unified public domain**.

```
                           +--------------------------------------------------+
                           |           Railway Edge & Public Domain           |
                           |       (e.g., https://astra-sense.up.railway.app) |
                           +--------------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------------+
|                                    SINGLE RAILWAY DOCKER CONTAINER                                      |
|                                                                                                         |
|   +---------------------------------------+               +-----------------------------------------+   |
|   |         React 19 + Vite 6 UI          |               |          FastAPI Engine (Python 3.11)   |   |
|   |   - Bundled in Stage 1 (/build/dist)  |  Relative     |   - Serves /health (Liveness Probe)     |   |
|   |   - Static assets (/app/static)       |<------------->|   - Serves /api/v1/* (Operational APIs) |   |
|   |   - SPA Fallback Route (index.html)   |  Requests     |   - Content Negotiation for Root /      |   |
|   |   - Same-origin (Zero CORS overhead)  |               |   - Strict JSON 404 for unhandled API   |   |
|   +---------------------------------------+               +-----------------------------------------+   |
|                                                                                |                        |
|                                                                                | ACID Transactions      |
|                                                                                v                        |
|                                   +-----------------------------------------------------------------+   |
|                                   |             Persistent Railway Volume Mount: /data              |   |
|                                   |  - Local Operational Source of Truth (SQLite 3 WAL)             |   |
|                                   |  - File: /data/orbital_guard.db (co-located -wal and -shm)      |   |
|                                   |  - Transactional Outbox (cloud_sync_outbox)                     |   |
|                                   |  - Conflict Resolution Engine (cloud_sync_conflicts)            |   |
|                                   +-----------------------------------------------------------------+   |
|                                                                                |                        |
+--------------------------------------------------------------------------------|------------------------+
                                                                                 |
                                                                                 | HTTPS / PostgREST
                                                                                 | Modern sb_secret_ Auth
                                                                                 v
                                                    +-----------------------------------------------------+
                                                    |              Supabase PostgreSQL Cloud              |
                                                    |  - Archival & Secondary Synchronization Destination |
                                                    |  - 10 Synchronized Tables                           |
                                                    |  - Row Level Security (RLS) Active                  |
                                                    |  - Automated RPC Reconciliation                     |
                                                    +-----------------------------------------------------+
```

### Key Architectural Tenets:
1. **Single Public Domain:** Both frontend dashboard and backend APIs share the identical domain, eliminating CORS friction and preventing hardcoded IP/host drift.
2. **Persistent Local Operational Primacy:** SQLite in WAL mode on a mounted persistent volume (`/data`) guarantees that mission-critical medical monitoring and telemetry ingestion continue unabated even during network partitions.
3. **Transactional Outbox & Dual-Database Sync:** Local writes and outbox event enqueueing occur atomically in a single SQLite transaction. An autonomous background worker replicates changes to Supabase PostgreSQL using modern `sb_secret_` credentials and exponential backoff with jitter.
4. **Resilient Routing & Content Negotiation:** Browser requests receive the React SPA; automated tests and API tools requesting JSON receive structured system status; invalid `/api/v1/*` routes return deterministic JSON 404s without falling back to HTML.

---

## 2. Multi-Stage Dockerfile Specifications

The deployment utilizes a production multi-stage `Dockerfile` (`Dockerfile`):

- **Stage 1 (Frontend Builder - `node:20-alpine`):**
  - Executes deterministic `npm ci` from `package-lock.json`.
  - Compiles the React 19 + Vite 6 application into minified assets at `/build/dist`.
- **Stage 2 (Runtime - `python:3.11-slim`):**
  - Installs lightweight system utilities (`curl`, `sqlite3`).
  - Installs Python dependencies (`fastapi`, `uvicorn`, `scikit-learn`, `numpy`, `pandas`, `httpx`, `google-genai`).
  - Ingests backend application code into `/app/backend`.
  - Ingests compiled frontend assets from Stage 1 into `/app/static`.
  - Prepares the persistent volume mount point `/data` (`chmod 777 /data`).
  - Executes container healthcheck against `/health`.
  - Starts Uvicorn listening on the dynamically assigned Railway `${PORT:-8000}`.

---

## 3. Step-by-Step Railway Deployment Instructions

### Step 1: Push Repository to GitHub
Ensure the latest code is pushed to your GitHub repository:
```bash
git push origin main
```

### Step 2: Create a New Project on Railway
1. Navigate to the Railway Console: [https://railway.app](https://railway.app).
2. Log in using your GitHub account.
3. Click **"New Project"** -> Select **"Deploy from GitHub repo"**.
4. Choose **`Sarthakadhav/ASTRA-SENSE-ORBITAL-GUARD`**.
5. Click **"Deploy Now"**.

### Step 3: Attach Persistent Storage Volume (/data)
> **CRITICAL:** Do NOT skip this step. SQLite requires persistent disk storage to survive container restarts and deployments.

1. In the Railway Project view, click on the newly created **ASTRA-SENSE-ORBITAL-GUARD** service.
2. Select the **"Volumes"** tab from the top navigation bar.
3. Click **"Add Volume"** (or "+ New Volume").
4. Configure the volume settings:
   - **Mount Path:** `/data`
5. Click **"Add"**. Railway will automatically mount this high-speed NVMe persistent volume to `/data` in your container.

> [!IMPORTANT]
> Railway enforces a single-replica policy when a volume is attached. This is ideal and required for SQLite WAL concurrency, preventing dual-writer database corruption.

### Step 4: Configure Environment Variables
Navigate to the **"Variables"** tab of the service and add the following production variables.

| Variable Name | Recommended Value | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | Enforces production mode and strict volume verification |
| `DATABASE_URL` | `sqlite:////data/orbital_guard.db` | Absolute path to persistent SQLite database on mounted volume |
| `STATIC_DIR` | `/app/static` | Path to compiled React frontend assets |
| `PORT` | `8000` | Fallback HTTP port (Railway automatically injects dynamic PORT) |
| `SUPABASE_URL` | `https://kgjbltqunjpscyipwgll.supabase.co` | Supabase Cloud API URL |
| `SUPABASE_SECRET_KEY` | *(Your Secret Key: sb_secret_...)* | Modern Supabase Secret Key for service-role PostgREST sync |
| `SUPABASE_PUBLISHABLE_KEY` | *(Your Publishable Key: sb_pub_...)* | Modern Supabase Publishable Key |
| `SUPABASE_SYNC_ENABLED` | `True` | Activates autonomous outbox worker loop |
| `SUPABASE_SYNC_INTERVAL_SECONDS`| `10` | Frequency of background outbox batch drain |
| `SUPABASE_SYNC_BATCH_SIZE` | `50` | Maximum records per synchronization cycle |
| `SUPABASE_MAX_RETRIES` | `5` | Maximum retry attempts before routing to Dead-Letter Queue |
| `GEMINI_API_KEY` | *(Optional Gemini API Key)* | Optional cloud intelligence enhancement key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model variant |

> [!CAUTION]
> Never commit actual secret keys (`sb_secret_...` or Gemini keys) to Git. Always inject them securely through the Railway Dashboard "Variables" interface.

### Step 5: Configure Custom Domain or Generate Railway Public Domain
1. In the service dashboard, navigate to **"Settings"**.
2. Scroll to the **"Networking"** section.
3. Click **"Generate Domain"** to receive an instant public URL (e.g., `astra-sense-orbital-guard-production.up.railway.app`).
4. (Optional) Click **"Custom Domain"** to bind your custom domain with automatic SSL/TLS termination.

---

## 4. Post-Deployment Verification & Smoke Tests

Once Railway marks the deployment **"Active"** (indicated by a green status indicator):

### 1. Healthcheck Probe
```bash
curl -i https://<your-railway-domain>/health
```
**Expected Response:**
```json
HTTP/2 200
content-type: application/json

{
  "status": "HEALTHY",
  "system": "ORBITAL GUARD / ASTRA SENSE",
  "version": "2.0.0",
  "environment": "production"
}
```

### 2. Frontend SPA Loading
Open `https://<your-railway-domain>/` in your browser.
- Verify the flight deck dashboard renders immediately.
- Test client-side routes directly in the browser address bar:
  - `/mission-medic`
  - `/crew-matrix`
  - `/cloud-sync`
- Refreshing any route must load the page cleanly without 404 errors.

### 3. API Relative Routing & 404 Guard
```bash
# Valid API endpoint
curl -s https://<your-railway-domain>/api/v1/system/status | jq .

# Non-existent API route (must return JSON 404, NEVER HTML index.html)
curl -i https://<your-railway-domain>/api/v1/nonexistent_test_route
```
**Expected 404 Response:**
```json
HTTP/2 404
content-type: application/json

{
  "detail": "API endpoint '/api/v1/nonexistent_test_route' not found"
}
```

### 4. Supabase Cloud Sync Verification
Navigate to `/cloud-sync` on the flight dashboard:
- Verify pipeline status displays **"CLOUD_CONNECTED"**.
- Click **"Trigger Sync Batch"** to verify instantaneous outbox drain to Supabase PostgreSQL.

---

## 5. Maintenance, Backups & Disaster Recovery

### Automatic Volume Persistence
When redeploying or pushing new commits to `main`:
- Railway creates a new container instance.
- The volume `/data` is detached from the previous container and attached to the new one.
- SQLite WAL files (`/data/orbital_guard.db`, `/data/orbital_guard.db-wal`, `/data/orbital_guard.db-shm`) remain completely intact.

### Manual Database Backup via Railway CLI
You can inspect or download a physical snapshot of the persistent SQLite database at any time using the Railway CLI:
```bash
# Connect to container shell
railway run --service ASTRA-SENSE-ORBITAL-GUARD sh

# Inside container: create a consistent vacuum backup
sqlite3 /data/orbital_guard.db "VACUUM INTO '/data/backup_manual.db'"
```

