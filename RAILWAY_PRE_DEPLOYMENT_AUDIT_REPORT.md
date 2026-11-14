# ASTRA SENSE – ORBITAL GUARD
# RAILWAY SINGLE-SERVICE DEPLOYMENT AUDIT REPORT

**Author:** Principal DevOps & Aerospace Systems Architect  
**Project:** ASTRA SENSE – ORBITAL GUARD  
**Date:** 2026-11-14  
**Scope:** Pre-Deployment Source Code, Architecture, and Storage Audit  

---

## 1. Executive Summary

This audit assesses the readiness of **ASTRA SENSE – ORBITAL GUARD** for deployment to Railway as a single combined service (1 Docker container, 1 Railway service, 1 public domain). The application unites a React 19 + Vite 6 frontend, a FastAPI Python backend, a local SQLite WAL operational database, and asynchronous Supabase cloud replication.

---

## 2. Codebase Component Inspection

### 2.1 Repository Directory Structure
```
ASTRA-SENSE-ORBITAL-GUARD/
├── backend/
│   ├── app/
│   │   ├── api/ (endpoints: telemetry, crew, health, alerts, inventory, incidents, dsn, system, auth, sync)
│   │   ├── core/ (auth, logging)
│   │   ├── database/ (connection.py, init_db.py, supabase_client.py)
│   │   ├── intelligence/ (anomaly_detection, decision_engine, telemetry_simulator)
│   │   ├── schemas/ (incident, inventory, sync, telemetry)
│   │   ├── services/ (sync_service.py)
│   │   ├── config.py
│   │   └── main.py
│   ├── requirements.txt
│   └── tests/ (test_backend.py, test_sync.py, test_phase_2_5_acceptance.py, test_phase_3_resilience.py)
├── src/ (React 19 + Vite 6 frontend components, context, services)
├── package.json & package-lock.json
├── vite.config.js
├── dist/ (Vite production build target)
├── scripts/ (maintenance, audit, backfill, testing scripts)
└── supabase/ (migrations: 00001, 00002, 00003)
```

### 2.2 Frontend Build & API Configuration
- **Framework:** React 18.3 / React 19 + Vite 6.0.
- **Lockfile:** `package-lock.json` is present and verified; enables deterministic `npm ci` builds.
- **Output Directory:** `dist/` containing `index.html` and `assets/`.
- **API Base URL:** Configured in `src/services/api.js` line 7 as `const API_BASE = '/api/v1'`.
- **Hardcoded Hosts:** 0 occurrences of `localhost` or `127.0.0.1` found across `src/`. All frontend requests use same-origin relative URLs.

### 2.3 Backend Entry Point & Framework
- **Entry Point:** `app.main:app` located at `backend/app/main.py`.
- **Lifespan Manager:** Initializes SQLite database via `init_database()` and handles graceful shutdown.
- **Router Prefix:** `/api/v1` (`settings.API_V1_STR`).
- **Health Checks:** Existing status check at `/api/v1/system/status`. A top-level `/health` endpoint is required for Railway health checks.
- **Static Assets:** Currently FastAPI serves JSON at `/`. Must be extended with `StaticFiles` and an SPA catch-all route serving `dist/index.html` without intercepting `/api/*`.

### 2.4 Database Path, Storage & WAL Mode
- **Current Connection Logic:** `backend/app/database/connection.py` uses `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, and `PRAGMA foreign_keys = ON`.
- **Current Path Resolution:** `settings.DATABASE_PATH` defaults to `BASE_DIR / "orbital_guard.db"`.
- **Railway Volume Mount Target:** `/data` directory.
- **Required Path Configuration:**
  - `DATABASE_URL=sqlite:////data/orbital_guard.db`
  - Automatic fallback: If `/data` exists and is writable, use `/data/orbital_guard.db`.
  - Sidecars: `-wal` and `-shm` sidecars reside automatically alongside `orbital_guard.db` in `/data`.
  - Startup Failure Guard: Must raise `RuntimeError` if production storage path `/data` is unavailable or non-writable.

### 2.5 Supabase Integration & Outbox Worker
- **Client:** `backend/app/database/supabase_client.py` using `httpx.AsyncClient`.
- **Header Behavior:** Modern `sb_secret_` opaque keys sent strictly via `apikey` header without `Authorization: Bearer`.
- **Outbox Worker:** `backend/app/services/sync_service.py` provides dependency-ordered synchronization, exponential backoff with jitter, dead-letter queue (`DEAD_LETTER`), and payload enrichment from local SQLite.
- **Worker Execution:** Adding an autonomous background loop to FastAPI `lifespan` ensures continuous outbox draining on Railway.

### 2.6 Authentication & Session State
- **Mechanism:** PBKDF2-HMAC-SHA256 with 100,000 iterations and unique cryptographic salts.
- **Session Tokens:** 8-hour shift lifetime (`SESSION_LIFETIME_SECONDS = 28800`) stored in `ACTIVE_SESSIONS` memory dictionary.
- **Restart Semantics:** Users re-authenticate following service restarts. Zero plaintext passwords stored.

---

## 3. Deployment Action Items

1. **Multi-Stage Dockerfile:** Multi-stage build (Node 20 Alpine for Vite compilation -> Python 3.11-slim runtime serving FastAPI + static assets).
2. **Mount Persistent `/data` in FastAPI:** Update `backend/app/config.py` and `backend/app/database/connection.py` to parse `DATABASE_URL` and support `/data/orbital_guard.db`.
3. **Integrate Frontend Static Serving in `main.py`:**
   - Mount `/assets` static files.
   - Add `/health` endpoint.
   - Add `{full_path:path}` SPA fallback serving `index.html`.
   - Ensure `/api/*` non-matching paths strictly return JSON 404.
4. **Autonomous Sync Worker in `lifespan`:** Start background loop in FastAPI `lifespan` with graceful shutdown signal handling.
5. **Railway Configuration (`railway.json`):** Single-replica container, health check at `/health`, volume mount at `/data`.
6. **Testing & Validation:** Execute full test battery, build container locally or test runtime paths, and produce deployment guide.

