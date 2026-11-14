# ASTRA SENSE – ORBITAL GUARD
## Phase 2.5 Modern Supabase Credential Compatibility Implementation Report

**Project:** ASTRA SENSE – ORBITAL GUARD  
**Subsystem:** Asynchronous Cloud Synchronization & Modern Supabase Credential Integration  
**Date:** November 13, 2026  
**Status:** IMPLEMENTED, LOCALLY VERIFIED, AWAITING LIVE APPROVAL  

---

## 1. Executive Summary

Supabase recently updated its API credential architecture from legacy long-lived JSON Web Tokens (`anon` / `service_role` JWTs) to modern opaque API keys:
- **`SUPABASE_SECRET_KEY`** (format: `sb_secret_...`) replacing `SUPABASE_SERVICE_ROLE_KEY`
- **`SUPABASE_PUBLISHABLE_KEY`** (format: `sb_publishable_...`) replacing `SUPABASE_ANON_KEY`
- **`SUPABASE_JWKS_URL`** (endpoint: `/.well-known/jwks.json`) for asymmetric JWT token verification

This implementation adapts the **ASTRA SENSE – ORBITAL GUARD** backend to fully support these modern credentials while strictly upholding the offline-first mandate:
1. **Zero Node.js / `@supabase/server` Dependencies:** Preserved 100% native Python asynchronous `httpx` transport.
2. **Elimination of the "Invalid JWT" Gateway Hazard:** Modern `sb_secret_...` keys are opaque strings rather than base64-encoded JWTs. Sending an `sb_secret_` token in `Authorization: Bearer <key>` causes PostgREST/Kong to reject requests with `401 Unauthorized ("Invalid JWT")`. The header builder now routes `sb_secret_` exclusively through `apikey: <key>`, while preserving legacy `Authorization: Bearer` behavior for existing JWTs.
3. **Dual-Key Fallback Resolution:** Non-breaking configuration allows developers to use either modern or legacy variable names seamlessly.
4. **Offline Isolation Intact:** Local SQLite WAL remains the sole operational source of truth. Offline clinical SOPs, deterministic life-safety checks, and local RBAC operate without any internet requirement.
5. **No Premature Cloud Ingestion:** Category C live tests and cloud backfill remain halted until explicit user authorization.

---

## 2. Modified Files & Exact Technical Changes

### A. Environment Configuration (`backend/app/config.py`)
- Added dual-key fallback resolution in `Settings`:
  - `SUPABASE_SECRET_KEY`: Resolved from `os.getenv("SUPABASE_SECRET_KEY")` with fallback to `os.getenv("SUPABASE_SERVICE_ROLE_KEY")`.
  - `SUPABASE_SERVICE_ROLE_KEY`: Alias pointing directly to `SUPABASE_SECRET_KEY` for 100% backward compatibility across older scripts.
  - `SUPABASE_PUBLISHABLE_KEY`: Resolved from `os.getenv("SUPABASE_PUBLISHABLE_KEY")` with fallback to `os.getenv("SUPABASE_ANON_KEY")`.
  - `SUPABASE_ANON_KEY`: Alias pointing directly to `SUPABASE_PUBLISHABLE_KEY`.
  - `SUPABASE_JWKS_URL`: Added as an optional setting.
- Maintained that backend synchronization requires **only** `SUPABASE_URL` and `SUPABASE_SECRET_KEY` (a publishable key is optional and never required for backend sync workers).

### B. HTTP Authentication Header Layer (`backend/app/database/supabase_client.py`)
- **Constructor:** Loads `settings.SUPABASE_SECRET_KEY` and `settings.SUPABASE_PUBLISHABLE_KEY` with fallback logic.
- **Header Dispatcher (`_get_headers`):**
  - Always populates `"apikey": self.key`.
  - If a user session JWT is passed (`user_jwt`), attaches `"Authorization": f"Bearer {user_jwt}"`.
  - Else if `self.key` is a legacy JWT (starts with `eyJ`), attaches `"Authorization": f"Bearer {self.key}"`.
  - For modern opaque keys (`sb_secret_...`), **omits the Authorization header entirely**, preventing PostgREST/Kong `Invalid JWT` parsing failures.
- **Consistent Application:** Updated across all cloud transport methods:
  - `test_connection()`: Fast health probe to `/rest/v1/`.
  - `upsert_record()`: Single record idempotent upsert.
  - `batch_upsert()`: Chunked outbox batch synchronization.
  - `call_rpc()`: Atomic PostgreSQL stored procedure invocation (`reconcile_inventory_transaction`).
- **Secret Scrubbing:** Unified via `_scrub_error()`, replacing both `self.key` and `self.anon_key` with `[REDACTED_KEY]` before logging or returning error dictionaries.

### C. Environment Templates (`.env.example` and `backend/.env.example`)
- Documented modern credential keys: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_PUBLISHABLE_KEY`, and `SUPABASE_JWKS_URL`.
- Documented legacy keys as commented backward-compatible fallbacks.

### D. Acceptance Test Suite (`backend/tests/test_phase_2_5_acceptance.py`)
- Added 4 isolated test cases under `CATEGORY A.2`:
  1. `test_modern_opaque_secret_key_header_behavior`: Validates that `sb_secret_` sets `apikey` without `Authorization: Bearer`, and correctly attaches user JWT when explicitly provided.
  2. `test_legacy_service_role_jwt_header_behavior`: Validates that legacy `eyJ...` tokens continue sending `Authorization: Bearer`.
  3. `test_credential_configuration_states`: Tests all 6 permutations of missing, partial, publishable-only, modern, and legacy credential states.
  4. `test_connection_failure_and_error_scrubbing_recovery`: Verifies that network failures scrub `sb_secret_` tokens from error strings and recover upon reconnect.
- Hardened Category B network recovery mocks to handle mixed outbox entity types (both table upserts and inventory RPC calls).

---

## 3. Test Verification Results

All tests executed with zero failures:

### A. Acceptance Test Suite (`pytest backend/tests/test_phase_2_5_acceptance.py -v`)
```text
collected 16 items

test_category_a_local_sqlite_schema_and_wal[asyncio]                     PASSED [  6%]
test_category_a_record_count_reconciliation[asyncio]                     PASSED [ 12%]
test_category_a_migration_preview_and_backup[asyncio]                   PASSED [ 18%]
test_category_a_transactional_outbox_rollback[asyncio]                  PASSED [ 25%]
test_category_a_server_side_role_authorization_enforcement[asyncio]     PASSED [ 31%]
test_category_a_secret_protection_and_scrubbing[asyncio]                PASSED [ 37%]
test_category_a_inventory_insufficient_stock_rejection[asyncio]         PASSED [ 43%]
test_modern_opaque_secret_key_header_behavior[asyncio]                  PASSED [ 50%]
test_legacy_service_role_jwt_header_behavior[asyncio]                   PASSED [ 56%]
test_credential_configuration_states[asyncio]                           PASSED [ 62%]
test_connection_failure_and_error_scrubbing_recovery[asyncio]          PASSED [ 68%]
test_category_b_network_partition_and_recovery_simulation[asyncio]     PASSED [ 75%]
test_category_b_partial_batch_failure_resilience[asyncio]               PASSED [ 81%]
test_category_b_mocked_inventory_ledger_reconciliation[asyncio]         PASSED [ 87%]
test_category_c_real_supabase_live_connectivity[asyncio]                SKIPPED [ 93%]
test_category_c_real_supabase_isolated_crud[asyncio]                    SKIPPED [100%]

======================= 14 passed, 2 skipped in 14.58s ========================
```
*(Category C tests cleanly skipped as designed until live project credentials are provided).*

### B. Complete Regression Suite (`pytest backend/tests/ -v`)
- **Total Tests:** 40 collected
- **Passed:** 38
- **Skipped:** 2 (Category C live integration)
- **Failed:** 0

### C. End-to-End Feature Verification (`python backend/test_all_features.py`)
- Subsystems Verified: 9 / 9 Subsystems PASSED (DB Init, Telemetry Simulator Modes A–D, Telemetry History, MedVault Inventory, Incidents Lifecycle, DSN Earth Sync Queue, Role-based Auth, Alerts Lifecycle).

### D. End-to-End Mission Scenario Validation (`python backend/test_scenarios_e2e.py`)
- Scenario 1 (Nominal Flight): PASSED
- Scenario 2 (Isolation Forest Fatigue Anomaly): PASSED
- Scenario 3 (Critical Hypoxia Emergency & Rule Engine): PASSED
- Scenario 4 (Autonomous Workload Redistribution): PASSED
- Scenario 5 (Offline Mission Continuity & MedVault): PASSED
- Scenario 6 (WAL Persistence & Process Restart): PASSED

### E. Frontend Production Build (`npm run build`)
- React 19 + Vite 6 + Tailwind CSS production bundle generated in `dist/` (1m 11s, 0 errors).

---

## 4. Security & Offline Independence Validation

1. **Automated Secret Scan:** Ran `python scripts/scan_secrets.py` across all repository files. Result: **0 leaked keys, 0 suspicious tokens**.
2. **Git Protection:** Verified `.gitignore` covers `.env`, `.env.*`, `backend/.env`, and `backend/.env.*`. Only `.env.example` templates are tracked.
3. **Server-Side RBAC Unaltered:** Student role remains restricted from privileged operations (`403 Forbidden`).
4. **PostgreSQL RPC Security:** `reconcile_inventory_transaction` retains `SECURITY DEFINER`, fixed `search_path = public, pg_temp;`, and execution restricted to `service_role`.
5. **Offline Independence:** With zero cloud credentials configured, the platform boots instantly, runs telemetry ingestion, scores anomalies with Isolation Forest, retrieves NASA SOPs, and logs transactional outbox events to SQLite WAL without hanging or crashing.

---

## 5. Required Local `.env` Configuration

To enable live synchronization with your Supabase project, create `backend/.env` with your project dashboard values:

```bash
# ==============================================================================
# ASTRA SENSE – ORBITAL GUARD: Local Environment Configuration
# ==============================================================================

ENVIRONMENT=flight_simulation
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Local Operational SQLite Database (Primary Offline-First Engine)
DATABASE_URL=sqlite:///./orbital_guard.db

# Modern Supabase Project Credentials (From your Supabase Project Dashboard):
SUPABASE_URL="https://<your-project-ref>.supabase.co"
SUPABASE_SECRET_KEY="sb_secret_<your-secret-key>"
SUPABASE_PUBLISHABLE_KEY="sb_publishable_<your-publishable-key>"
SUPABASE_JWKS_URL="https://<your-project-ref>.supabase.co/auth/v1/.well-known/jwks.json"

# Cloud Synchronization Engine Settings
SUPABASE_SYNC_ENABLED=True
SUPABASE_SYNC_INTERVAL_SECONDS=10
SUPABASE_SYNC_BATCH_SIZE=50
SUPABASE_MAX_RETRIES=5

# DSN Simulation & Mission Elapsed Time
DSN_LATENCY_SECONDS=862
DEFAULT_MET_DAYS=142
```

*(Note: Never commit `backend/.env` to GitHub. The file is already ignored by `.gitignore`).*

---

## 6. Remaining Blockers & Next Actions

| Task | Status | Requirement |
| :--- | :---: | :--- |
| **Apply Supabase Migrations** | Pending User Action | Apply `supabase/migrations/00001_initial_schema.sql`, `00002_row_level_security.sql`, and `00003_reconciliation_and_triggers.sql` in the Supabase SQL Editor. |
| **Set `backend/.env`** | Pending User Action | Populate `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in `backend/.env`. |
| **Execute Category C Tests** | Awaiting Approval | Run `python -m pytest backend/tests/test_phase_2_5_acceptance.py -k test_category_c -v` once configured. |
| **Execute Live Backfill** | Awaiting Approval | Run `python scripts/migrate_sqlite_to_supabase.py` to synchronize 214 existing SQLite records. |

**In accordance with your instructions, all local implementation and testing is complete. The system is stopped and awaiting your explicit approval before performing any live cloud migrations or backfill.**

