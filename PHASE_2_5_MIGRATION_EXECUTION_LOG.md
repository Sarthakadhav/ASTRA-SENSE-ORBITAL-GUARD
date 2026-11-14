# ASTRA SENSE – ORBITAL GUARD
## Phase 2.5 Migration Execution Log & Audit Trail

**Project:** ASTRA SENSE – ORBITAL GUARD  
**Supabase Reference:** `kgjbltqunjpscyipwgll`  
**Host:** `https://kgjbltqunjpscyipwgll.supabase.co`  
**Date:** November 13, 2026  
**Status:** MIGRATIONS AUDITED, HARDENED & PREPARED FOR EXECUTION  

---

## 1. Migration Manifest & Dependency Order

The migrations are designed in strict dependency order: parent tables first, followed by child tables, security policies, and stored procedures.

```text
MIGRATION 1: supabase/migrations/00001_initial_schema.sql
  ├── Parent Tables: public.astronauts, public.medical_inventory
  ├── Child Tables: public.telemetry_history, public.health_alerts, public.recovery_timelines, public.incidents, public.inventory_dispensations
  ├── Sync Infrastructure: public.audit_logs, public.cloud_sync_ledger, public.cloud_sync_conflicts
  └── 8 Performance Indexes: idx_supabase_telemetry_ast_time, idx_supabase_health_alerts_ast, etc.

MIGRATION 2: supabase/migrations/00002_row_level_security.sql (Hardened)
  ├── ALTER TABLE ... ENABLE ROW LEVEL SECURITY (All 10 tables)
  ├── Idempotent Cleanup: DROP POLICY IF EXISTS in DO $$ block
  ├── service_role Access: Full CRUD permissions for backend sync engine
  └── Zero-Trust Role Access: Denies direct browser/anon access to protect PHI

MIGRATION 3: supabase/migrations/00003_reconciliation_and_triggers.sql
  ├── Function: update_updated_at_column()
  ├── Triggers: trigger_update_astronauts_time, trigger_update_inventory_time, trigger_update_recovery_time
  ├── Stored Procedure: reconcile_inventory_transaction(...)
  └── Privileges: REVOKE ALL FROM PUBLIC, anon; GRANT EXECUTE TO service_role;
```

---

## 2. Pre-Execution Safety Inspection

| Migration File | Destructive Statements | Idempotency Safeguards | Execution Safety Rating |
| :--- | :---: | :---: | :---: |
| **`00001_initial_schema.sql`** | 0 (`DROP`, `TRUNCATE`, `ALTER DROP` absent) | `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS` | **SAFE TO EXECUTE** |
| **`00002_row_level_security.sql`** | 0 | `DROP POLICY IF EXISTS` inside PL/pgSQL `DO $$` block | **SAFE TO EXECUTE** |
| **`00003_reconciliation_and_triggers.sql`** | 0 | `CREATE OR REPLACE FUNCTION`, `DROP TRIGGER IF EXISTS` | **SAFE TO EXECUTE** |

---

## 3. Execution Environment & Technical Constraints

1. **Protocol Analysis:**
   - The backend is authenticated to Supabase via PostgREST using `SUPABASE_SECRET_KEY` (`sb_secret_...`).
   - PostgREST is an HTTP interface designed strictly for Data Manipulation (DML - `SELECT`, `INSERT`, `UPDATE`, `DELETE`, and `RPC`).
   - PostgREST does **not** expose endpoints for executing raw Data Definition Language (DDL - `CREATE TABLE`, `CREATE TRIGGER`).
2. **Database Connection String (`SUPABASE_DB_URL`):**
   - Direct connection string (`postgresql://postgres.kgjbltqunjpscyipwgll:[password]@...`) is not configured in `backend/.env`.
3. **Execution Path:**
   - The 3 SQL files must be executed through the **Supabase Dashboard SQL Editor** at `https://supabase.com/dashboard/project/kgjbltqunjpscyipwgll/sql`.

---

## 4. Execution Step-by-Step Instructions

Execute the following 3 scripts in sequence in your Supabase SQL Editor:

### Step 1: Execute `00001_initial_schema.sql`
- **File:** [`supabase/migrations/00001_initial_schema.sql`](file:///d:/ASTRA-SENSE-ORBITAL-GUARD/supabase/migrations/00001_initial_schema.sql)
- **Expected Result:** Creates all 10 tables, primary keys, foreign keys, unique constraints, and 8 performance indexes.
- **Verification:** PostgREST endpoints `/rest/v1/astronauts`, `/rest/v1/medical_inventory`, etc. will return HTTP 200 instead of 404.

### Step 2: Execute `00002_row_level_security.sql`
- **File:** [`supabase/migrations/00002_row_level_security.sql`](file:///d:/ASTRA-SENSE-ORBITAL-GUARD/supabase/migrations/00002_row_level_security.sql)
- **Expected Result:** Enables Row Level Security on all 10 tables. Establishes full sync access for `service_role` and denies direct public/browser access.

### Step 3: Execute `00003_reconciliation_and_triggers.sql`
- **File:** [`supabase/migrations/00003_reconciliation_and_triggers.sql`](file:///d:/ASTRA-SENSE-ORBITAL-GUARD/supabase/migrations/00003_reconciliation_and_triggers.sql)
- **Expected Result:** Registers `reconcile_inventory_transaction` with `SECURITY DEFINER` and restricted `service_role` execution privileges.

---

## 5. Rollback & Disaster Recovery Plan

In the event of an unexpected syntax or permission error during migration:
- Because all statements use `IF NOT EXISTS` and `CREATE OR REPLACE`, rerunning the scripts is inherently idempotent and non-destructive.
- The local operational flight database (`backend/orbital_guard.db`) remains completely untouched in SQLite WAL mode.
- A verified backup exists at `backend/backups/orbital_guard_phase_2_5_20261113_143338.db` (389,120 bytes).

