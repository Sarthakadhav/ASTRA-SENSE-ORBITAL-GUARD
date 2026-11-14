# ASTRA SENSE – ORBITAL GUARD
## Phase 2.5 Live Supabase Read-Only Preflight Diagnostic Report

**Project:** ASTRA SENSE – ORBITAL GUARD  
**Target:** Supabase PostgreSQL Cloud Sync Project (`kgjbltqunjpscyipwgll.supabase.co`)  
**Execution Mode:** Read-Only Diagnostic (Zero cloud modifications, zero data mutations)  
**Date:** November 13, 2026  
**Final Verdict:** **NOT READY (Pending Real Secret Key Entry)**  

---

## 1. Executive Summary

A comprehensive, non-destructive **Read-Only Live Connection Preflight** was executed against the configured Supabase target. The test evaluated actual network reachability, public cryptographic endpoints, API gateway response patterns, credential detection, and local SQLite data inventory.

### Key Takeaways:
1. **Network Infrastructure:** The Supabase project host `kgjbltqunjpscyipwgll.supabase.co` is **active, reachable, and online**.
2. **Public Gateway & JWKS:** 
   - The JWKS cryptographic endpoint (`/auth/v1/.well-known/jwks.json`) returned **HTTP 200 OK** with 1 active public RSA/EC key.
   - The PostgREST root gateway (`/rest/v1/`) responded with **HTTP 401 ("No API key found in request")**, confirming that the API gateway is operational and correctly demanding API authentication.
3. **Credential Detection Blocker:** 
   - `SUPABASE_URL` and `SUPABASE_JWKS_URL` are properly detected.
   - However, the `SUPABASE_SECRET_KEY` and `SUPABASE_PUBLISHABLE_KEY` values in `backend/.env` currently contain the literal placeholder text:  
     `"PASTE_YOUR_SUPABASE_SECRET_KEY_HERE"` and `"PASTE_YOUR_SUPABASE_PUBLISHABLE_KEY_HERE"`.
   - The backend safety layer correctly flagged this placeholder and kept the synchronization pipeline in safe `LOCAL_ONLY` offline mode (`is_configured: False`), preventing any unauthorized or malformed requests to Supabase.
4. **Local Data Readiness:** The local SQLite WAL database contains **303 operational records** across the 8 core flight tables, 100% verified and ready for migration once credentials are confirmed.

---

## 2. Credential Detection Status (Zero Secrets Logged)

| Parameter | Detection Status | Verified Format / Type | Safety Note |
| :--- | :---: | :--- | :--- |
| **`SUPABASE_URL`** | Detected | `https://kgjbltqunjpscyipwgll.supabase.co` | HTTPS verified, domain active |
| **`SUPABASE_SECRET_KEY`** | **BLOCKER** | Length: 35 chars (`PASTE_YOUR_...`) | Placeholder string detected on disk |
| **`SUPABASE_PUBLISHABLE_KEY`** | Detected | Length: 40 chars (`PASTE_YOUR_...`) | Placeholder string detected on disk |
| **`SUPABASE_JWKS_URL`** | Detected | `https://kgjbltqunjpscyipwgll.supabase.co/auth/v1/...` | Valid URL, public key active |
| **`supabase_manager.is_configured`** | Safe Guard | `False` | Properly prevented live traffic with placeholder |

*(Zero credentials or authorization tokens were exposed, printed, or written to reports).*

---

## 3. Network Connectivity & HTTP Status

| Target Endpoint | Method | Response Status | Diagnostic Output |
| :--- | :---: | :---: | :--- |
| **JWKS Public Key Endpoint**<br>`/auth/v1/.well-known/jwks.json` | `GET` | **200 OK** | Endpoint reachable. Returned 1 active public verification key. |
| **PostgREST API Gateway**<br>`/rest/v1/` | `GET` | **401 Unauthorized** | Gateway online. Rejected unauthenticated request (`"No apikey request header"`). |
| **Client Manager Probe**<br>`supabase_manager.test_connection()` | `GET` | `NOT_CONFIGURED` | Pipeline safely engaged local SQLite WAL offline fallback. |

---

## 4. Database Schema & RPC Inspection

Because the secret key in `backend/.env` is currently the template placeholder `"PASTE_YOUR_SUPABASE_SECRET_KEY_HERE"`, authenticated introspection of PostgreSQL tables via PostgREST was safely blocked to prevent authentication spam.

### Expected Cloud Objects (To Be Verified Upon Key Entry):
1. **Core Operational Tables (8):**
   - `public.astronauts`
   - `public.medical_inventory`
   - `public.recovery_timelines`
   - `public.health_alerts`
   - `public.incidents`
   - `public.inventory_dispensations`
   - `public.telemetry_history`
   - `public.audit_logs`
2. **Sync Infrastructure Tables (2):**
   - `public.cloud_sync_ledger`
   - `public.cloud_sync_conflicts`
3. **Stored Procedures (RPC):**
   - `public.reconcile_inventory_transaction(...)`

---

## 5. Local Data Inventory & Migration Readiness

The local SQLite flight database (`backend/orbital_guard.db`) was audited under WAL mode:

| Table Name | Entity Type | Local Record Count | Backfill Target Status |
| :--- | :--- | :---: | :--- |
| `astronauts` | Crew Baseline & Readiness | 4 | Ready |
| `medical_inventory` | MedVault Stock Ledger | 18 | Ready |
| `recovery_timelines` | Mission Recovery Schedules | 2 | Ready |
| `health_alerts` | Deterministic Safety Alerts | 4 | Ready |
| `incidents` | Medical & System Incidents | 44 | Ready |
| `inventory_dispensations` | Immutable Consumption Logs | 24 | Ready |
| `telemetry_history` | High-Frequency Physiological Records | 109 | Ready |
| `audit_logs` | Immutable Flight Audit Trail | 98 | Ready |
| **Total Core Operational Records** | | **303 records** | **100% Validated** |
| `cloud_sync_ledger` | Sync Reconciliation Ledger | 0 | Local empty / Cloud target |
| `cloud_sync_conflicts` | Conflict Resolution Queue | 1 | Preserved for review |

---

## 6. Blockers & Recommended Next Actions

### Identified Blocker
- **Incomplete Credential Input in `backend/.env`:**  
  The file `backend/.env` currently holds the placeholder string `PASTE_YOUR_SUPABASE_SECRET_KEY_HERE`.

### Step-by-Step Resolution:
1. **Update `backend/.env`:**
   Open `backend/.env` in your editor and replace:
   ```env
   SUPABASE_SECRET_KEY=PASTE_YOUR_SUPABASE_SECRET_KEY_HERE
   ```
   with your actual project Secret Key (copied from your Supabase Dashboard under **Project Settings -> API -> Secret Key**, starting with `sb_secret_` or legacy `eyJ...`).
2. **Apply Supabase SQL Migrations:**
   Ensure the following 3 SQL migrations have been executed in your Supabase SQL Editor:
   - `supabase/migrations/00001_initial_schema.sql`
   - `supabase/migrations/00002_row_level_security.sql`
   - `supabase/migrations/00003_reconciliation_and_triggers.sql`
3. **Re-Run Read-Only Preflight:**
   Once saved, I will immediately run the authenticated schema inspection to confirm that all 10 tables and the RPC function exist and match the application contract.

---

## 7. Final Verdict

# [NOT READY — AWAITING REAL SECRET KEY IN `backend/.env`]

- **Network Layer:** **READY (Reachable & Responsive)**
- **Gateway Layer:** **READY (Online & Enforcing Auth)**
- **Local Data Layer:** **READY (303 records validated in SQLite WAL)**
- **Authentication Layer:** **BLOCKED (Placeholder key detected on disk)**

*The platform remains 100% operational in offline flight simulation mode. No live cloud mutations, migrations, or sync writes were performed.*

