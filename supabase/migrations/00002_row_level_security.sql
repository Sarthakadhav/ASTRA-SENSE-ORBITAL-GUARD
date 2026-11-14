-- ==============================================================================
-- ASTRA SENSE – ORBITAL GUARD
-- Supabase Row Level Security (RLS) & Access Control Migration
-- Version: 00002_row_level_security.sql (Hardened for Phase 2.5)
-- Description: Enables RLS on all 10 mission tables and enforces strict least-privilege policies.
-- 
-- SECURITY DESIGN & AUDIT RATIONALE (Phase 2.5 Hardening):
-- 1. The FastAPI backend connects using the service_role key to perform trusted
--    bidirectional sync worker operations. Service role has full CRUD on all tables.
-- 2. Direct browser / public access via PostgREST is STRICTLY DENIED for both 'anon'
--    and 'authenticated' roles. Blanket 'USING (true)' for authenticated users is eliminated
--    to prevent unauthorized cross-tenant scraping of Protected Health Information (PHI).
-- 3. Astronaut authentication and role-based permissions (Student, Tester, Faculty)
--    are enforced server-side by the FastAPI application layer (/api/v1/...) before
--    any read or write operation is permitted.
-- ==============================================================================

-- 1. Enable Row Level Security on all 10 public tables
ALTER TABLE public.astronauts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telemetry_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.health_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medical_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_dispensations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recovery_timelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cloud_sync_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cloud_sync_conflicts ENABLE ROW LEVEL SECURITY;

-- 2. Drop existing policies if any (Ensures 100% idempotency across re-runs)
DO $$
BEGIN
    -- Astronauts
    DROP POLICY IF EXISTS "Deny anonymous public access to astronauts" ON public.astronauts;
    DROP POLICY IF EXISTS "Allow authenticated read on astronauts" ON public.astronauts;
    DROP POLICY IF EXISTS "Service role full access on astronauts" ON public.astronauts;
    
    -- Telemetry History
    DROP POLICY IF EXISTS "Deny anonymous access to telemetry" ON public.telemetry_history;
    DROP POLICY IF EXISTS "Allow authenticated read on telemetry" ON public.telemetry_history;
    DROP POLICY IF EXISTS "Service role full access on telemetry" ON public.telemetry_history;
    
    -- Health Alerts
    DROP POLICY IF EXISTS "Deny anonymous access to health alerts" ON public.health_alerts;
    DROP POLICY IF EXISTS "Allow authenticated read on health alerts" ON public.health_alerts;
    DROP POLICY IF EXISTS "Service role full access on health alerts" ON public.health_alerts;
    
    -- Medical Inventory
    DROP POLICY IF EXISTS "Deny anonymous access to inventory" ON public.medical_inventory;
    DROP POLICY IF EXISTS "Allow authenticated read on inventory" ON public.medical_inventory;
    DROP POLICY IF EXISTS "Service role full access on inventory" ON public.medical_inventory;
    
    -- Inventory Dispensations
    DROP POLICY IF EXISTS "Deny anonymous access to dispensations" ON public.inventory_dispensations;
    DROP POLICY IF EXISTS "Allow authenticated read on dispensations" ON public.inventory_dispensations;
    DROP POLICY IF EXISTS "Service role full access on dispensations" ON public.inventory_dispensations;
    
    -- Incidents
    DROP POLICY IF EXISTS "Deny anonymous access to incidents" ON public.incidents;
    DROP POLICY IF EXISTS "Allow authenticated read on incidents" ON public.incidents;
    DROP POLICY IF EXISTS "Service role full access on incidents" ON public.incidents;
    
    -- Audit Logs
    DROP POLICY IF EXISTS "Deny anonymous access to audit logs" ON public.audit_logs;
    DROP POLICY IF EXISTS "Allow authenticated read on audit logs" ON public.audit_logs;
    DROP POLICY IF EXISTS "Service role full access on audit logs" ON public.audit_logs;

    -- Recovery Timelines
    DROP POLICY IF EXISTS "Deny anonymous access to recovery timelines" ON public.recovery_timelines;
    DROP POLICY IF EXISTS "Allow authenticated read on recovery timelines" ON public.recovery_timelines;
    DROP POLICY IF EXISTS "Service role full access on recovery timelines" ON public.recovery_timelines;

    -- Cloud Sync Ledger
    DROP POLICY IF EXISTS "Deny anonymous access to sync ledger" ON public.cloud_sync_ledger;
    DROP POLICY IF EXISTS "Allow authenticated read on sync ledger" ON public.cloud_sync_ledger;
    DROP POLICY IF EXISTS "Service role full access on sync ledger" ON public.cloud_sync_ledger;

    -- Cloud Sync Conflicts
    DROP POLICY IF EXISTS "Deny anonymous access to sync conflicts" ON public.cloud_sync_conflicts;
    DROP POLICY IF EXISTS "Allow authenticated read on sync conflicts" ON public.cloud_sync_conflicts;
    DROP POLICY IF EXISTS "Service role full access on sync conflicts" ON public.cloud_sync_conflicts;
END $$;

-- 3. Policy: Service Role Full Access (For Backend Sync Worker)
-- Authorizes the backend sync engine (using SUPABASE_SECRET_KEY) to replicate outbox events.
CREATE POLICY "Service role full access on astronauts"
    ON public.astronauts FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on telemetry"
    ON public.telemetry_history FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on health alerts"
    ON public.health_alerts FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on inventory"
    ON public.medical_inventory FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on dispensations"
    ON public.inventory_dispensations FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on incidents"
    ON public.incidents FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on audit logs"
    ON public.audit_logs FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on recovery timelines"
    ON public.recovery_timelines FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on sync ledger"
    ON public.cloud_sync_ledger FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on sync conflicts"
    ON public.cloud_sync_conflicts FOR ALL
    TO service_role USING (true) WITH CHECK (true);

-- 4. Zero-Trust Access Policy for 'anon' and 'authenticated' browser roles
-- Astronaut biometrics, mental fatigue states, and medications constitute Protected Health Information (PHI).
-- Direct PostgREST queries from browser tokens without backend authorization return 0 rows.
-- Authorized access is mediated exclusively through FastAPI endpoints with server-side RBAC validation.
