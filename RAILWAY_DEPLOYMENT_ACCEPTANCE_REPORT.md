# ASTRA SENSE – ORBITAL GUARD
# Complete Railway Single-Service Deployment Acceptance Report

**Author:** Antigravity DevOps & Principal Systems Architect  
**Project:** ASTRA SENSE – ORBITAL GUARD  
**Target Environment:** Railway Single-Service Container  
**Date of Acceptance:** November 14, 2026  
**Status:** FULLY ACCEPTED & PRODUCTION READY  

---

## 1. Executive Summary

This report establishes complete formal verification of the single-service Railway deployment architecture for **ASTRA SENSE – ORBITAL GUARD**.

The application has been unified into a single Docker container serving:
1. **React 19 + Vite 6 Frontend:** Static assets, root route `/`, and SPA client-side fallback routes (`index.html`).
2. **FastAPI Backend:** `/health` liveness probe, `/api/v1/*` flight APIs, and API documentation at `/docs`.
3. **Local Operational Database:** SQLite in Write-Ahead Logging (`WAL`) mode with persistent volume storage mounted at `/data`.
4. **Cloud Database Archival:** Preserved asynchronous Supabase PostgreSQL replication via transactional outbox (`cloud_sync_outbox`) and conflict resolution ledger (`cloud_sync_conflicts`).

All legacy Vercel serverless artifacts and dependencies have been removed.

---

## 2. Architecture & File Manifest

| File / Component | Purpose | Status |
|---|---|---|
| `Dockerfile` | Multi-stage build (`node:20-alpine` -> `python:3.11-slim`) | Created & Verified |
| `.dockerignore` | Exclusion of `.env`, `*.db`, `node_modules`, `dist`, `.git` | Created & Verified |
| `railway.json` | Declarative Railway configuration, healthcheck probe, restart policy | Created & Verified |
| `backend/app/config.py` | Strict `/data` volume detection and `DATABASE_URL` path parser | Hardened & Verified |
| `backend/app/database/connection.py` | SQLite WAL connection manager with dynamic parent directory creation | Hardened & Verified |
| `backend/app/main.py` | Content negotiation root route, SPA router, JSON 404 guard, sync worker | Hardened & Verified |
| `src/services/api.js` | Same-origin relative API pathing (`/api/v1`) | Verified (0 hardcoded IPs) |
| `vercel.json` | Legacy Vercel configuration | Removed |
| `api/` | Legacy Vercel serverless wrapper | Removed |

---

## 3. Verification Test Battery & Evidence

### 3.1 Secret & Credential Leak Scan
- **Command:** `python scripts/scan_secrets.py`
- **Result:**
  ```text
  Secret scan completed. Found 0 suspicious tokens.
  Return code: 0
  ```
- **Finding:** Zero hardcoded `sb_secret_`, `eyJ...` service role tokens, or private credentials exist in the codebase, Dockerfile, or git index.

### 3.2 Frontend Production Compilation
- **Command:** `npm run build`
- **Result:**
  ```text
  vite v6.4.5 building for production...
  ✓ 2682 modules transformed.
  dist/index.html                   1.01 kB │ gzip:   0.61 kB
  dist/assets/index-CicdQGNF.css   39.06 kB │ gzip:   6.97 kB
  dist/assets/index-DsDJbJQQ.js   733.20 kB │ gzip: 198.39 kB
  ✓ built in 1m 15s
  ```
- **Finding:** Clean production build with complete asset bundling and zero compilation errors.

### 3.3 Core Pytest Test Suite
- **Command:** `python -m pytest backend/tests/ -v`
- **Result:** **44 / 44 PASSED (100%)**
  - Category A Local SQLite Schema & WAL: PASSED
  - Category A Record Count Reconciliation: PASSED
  - Category A Transactional Outbox Rollback: PASSED
  - Category A Server-Side Role Authorization: PASSED
  - Category A Secret Scrubbing: PASSED
  - Category A Inventory Stock Rejection: PASSED
  - Category B Network Partition & Recovery: PASSED
  - Category B Partial Batch Failure Resilience: PASSED
  - Category B Inventory Ledger Reconciliation: PASSED
  - Category C Real Supabase Live Connectivity: PASSED
  - Category C Real Supabase Isolated CRUD: PASSED
  - Phase 3 Subsystem Tests (Modules 1-7): ALL PASSED
  - Synchronizer & Dependency Ordering Tests: ALL PASSED

### 3.4 Extended Subsystem Feature Verification
- **Command:** `python backend/test_all_features.py`
- **Result:** **9 / 9 Subsystems Passed**
  1. DB Initialization & Vance/Chen Baseline Reset: PASSED
  2. Telemetry Simulator Scenarios (`NORMAL`, `FATIGUE`, `HYPOXIA`, `CARDIAC`, `CUSTOM`): PASSED
  3. Telemetry Ingestion Pipeline & Deduplication: PASSED
  4. Telemetry History & Latest Query: PASSED
  5. MedVault Operations (Replenish, Add Item, Dispense): PASSED
  6. Incidents Create & Resolve Lifecycle: PASSED
  7. DSN Earth Sync Queue Transmission: PASSED
  8. Role-Based Authentication (Student vs Faculty/Flight Surgeon): PASSED
  9. Alerts Lifecycle (Acknowledge & Resolve): PASSED

### 3.5 End-to-End Mission Scenario Validation
- **Command:** `python backend/test_scenarios_e2e.py`
- **Result:** **6 / 6 Scenarios Passed**
  - Scenario 1 (Normal Mission Operation Mode A): PASSED
  - Scenario 2 (Fatigue Detection & Explainable Isolation Forest Mode B): PASSED
  - Scenario 3 (Hypoxia Emergency Safety Alert Mode C): PASSED
  - Scenario 4 (Autonomous Crew Readiness & Workload Reassignment): PASSED
  - Scenario 5 (Offline Mission Continuity & Zero-Network SOP Latency 0.13ms): PASSED
  - Scenario 6 (Database Persistence & Process Restart Integrity): PASSED

### 3.6 Failure Simulation & Resilience Test Suite
- **Command:** `python scripts/test_failure_simulation.py`
- **Result:** **4 / 4 Simulations Passed**
  - Simulation 1 (DSN Link Blackout & Offline Flight Primacy): PASSED
  - Simulation 2 (DSN Link Restoration & 44-event Outbox Drain): PASSED
  - Simulation 3 (Corrupt Payload Quarantine to Dead-Letter Queue): PASSED
  - Simulation 4 (MedVault Over-Draw Boundary Guard): PASSED

### 3.7 Routing, SPA Catch-All & Healthcheck Verification
- **Test:** Synthetic HTTP client tests simulating browser navigation vs automated API calls.
- **Results:**
  - `GET /health` -> `HTTP 200` JSON `{"status": "HEALTHY", "system": "ORBITAL GUARD / ASTRA SENSE"}`
  - `GET /` with `Accept: text/html` -> `HTTP 200` HTML (Serves `dist/index.html`)
  - `GET /` with `Accept: application/json` -> `HTTP 200` JSON (Flight status response)
  - `GET /mission-medic` -> `HTTP 200` HTML (Client-side routing fallback)
  - `GET /crew-matrix` -> `HTTP 200` HTML (Client-side routing fallback)
  - `GET /api/v1/nonexistent` -> `HTTP 404` JSON `{"detail": "API endpoint '/api/v1/nonexistent' not found"}`
  - `GET /api/invalid` -> `HTTP 404` JSON `{"detail": "API endpoint '/api/invalid' not found"}`

### 3.8 Database WAL Integrity & Pre-Deployment Record Counts
- **PRAGMA integrity_check:** `ok`
- **PRAGMA journal_mode:** `wal`
- **Active Record Counts:**
  - `astronauts`: 4
  - `medical_inventory`: 23
  - `recovery_timelines`: 2
  - `health_alerts`: 4
  - `incidents`: 67
  - `inventory_dispensations`: 38
  - `telemetry_history`: 171
  - `audit_logs`: 154
  - `cloud_sync_outbox`: 545
  - `cloud_sync_conflicts`: 1

---

## 4. Production Readiness Conclusion

The repository is fully verified and prepared for single-service deployment to Railway:
- **Zero Configuration Ambiguity:** Dockerfile and `railway.json` provide deterministic, automated container building and health probing.
- **Storage Permanence:** Strict `/data` persistent volume detection ensures zero risk of SQLite data loss across container lifecycles.
- **Security Hardened:** All secrets are externalized to environment variables; all API endpoints enforce strict JSON responses and role validation.

