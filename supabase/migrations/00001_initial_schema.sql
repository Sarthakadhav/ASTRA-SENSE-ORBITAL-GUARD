-- ==============================================================================
-- ASTRA SENSE – ORBITAL GUARD
-- Supabase PostgreSQL Initial Schema Migration
-- Version: 00001_initial_schema.sql
-- Description: Creates core mission tables, indexes, and foreign keys mapped from SQLite
-- ==============================================================================

-- 1. Astronaut Profiles Table
CREATE TABLE IF NOT EXISTS public.astronauts (
    id VARCHAR(32) PRIMARY KEY,
    name TEXT NOT NULL,
    callsign TEXT,
    role TEXT NOT NULL,
    "dutyCategory" TEXT NOT NULL,
    condition TEXT NOT NULL,
    "conditionSeverity" TEXT NOT NULL,
    photo TEXT,
    avatar TEXT,
    age INTEGER,
    "bloodType" VARCHAR(8),
    "missionDay" INTEGER,
    "suitId" VARCHAR(32),
    "readinessScore" INTEGER,
    "readinessBreakdown" JSONB DEFAULT '{}'::jsonb,
    vitals JSONB DEFAULT '{}'::jsonb,
    "sensorReliability" JSONB DEFAULT '{}'::jsonb,
    "mlModel" JSONB DEFAULT '{}'::jsonb,
    responsibilities JSONB DEFAULT '[]'::jsonb,
    "backupOfficer" JSONB DEFAULT '{}'::jsonb,
    recommendation TEXT,
    "assignedBackupId" VARCHAR(32),
    "isReassigned" BOOLEAN DEFAULT FALSE,
    "timelineNotes" TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Telemetry History Table (Append-only high frequency time-series)
CREATE TABLE IF NOT EXISTS public.telemetry_history (
    id BIGSERIAL PRIMARY KEY,
    sync_id VARCHAR(64) UNIQUE,
    packet_id BIGINT,
    astronaut_id VARCHAR(32) REFERENCES public.astronauts(id) ON DELETE CASCADE,
    timestamp_met VARCHAR(32),
    ecg_lead2_mv DOUBLE PRECISION,
    spo2_pct DOUBLE PRECISION,
    heart_rate_bpm DOUBLE PRECISION,
    skin_temp_c DOUBLE PRECISION,
    imu_accel_g JSONB,
    impedance_ohms DOUBLE PRECISION,
    battery_level_pct DOUBLE PRECISION,
    crc32_valid BOOLEAN DEFAULT TRUE,
    quality_status VARCHAR(32),
    anomaly_score DOUBLE PRECISION,
    is_anomaly BOOLEAN DEFAULT FALSE,
    is_simulated BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Health Alerts Table
CREATE TABLE IF NOT EXISTS public.health_alerts (
    id VARCHAR(64) PRIMARY KEY,
    astronaut_id VARCHAR(32) REFERENCES public.astronauts(id) ON DELETE CASCADE,
    severity VARCHAR(32) NOT NULL,
    type VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(32) DEFAULT 'NEW',
    source VARCHAR(64) DEFAULT 'LOCAL_HEALTH_ENGINE',
    created_at_met VARCHAR(32) NOT NULL,
    acknowledged_by VARCHAR(64),
    acknowledged_at_met VARCHAR(32),
    resolved_by VARCHAR(64),
    resolved_at_met VARCHAR(32),
    actions_taken JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Medical Inventory Table
CREATE TABLE IF NOT EXISTS public.medical_inventory (
    id VARCHAR(32) PRIMARY KEY,
    category VARCHAR(64) NOT NULL,
    name TEXT NOT NULL,
    indication TEXT,
    stock INTEGER NOT NULL,
    unit VARCHAR(32) NOT NULL,
    "minSafeStock" INTEGER NOT NULL,
    "shelfLifeDays" INTEGER NOT NULL,
    "radiationDegradationRate" VARCHAR(32),
    "vitalUrgency" VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    location VARCHAR(64),
    contraindications TEXT,
    "batteryChargePercent" INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Inventory Dispensations Table
CREATE TABLE IF NOT EXISTS public.inventory_dispensations (
    id BIGSERIAL PRIMARY KEY,
    sync_id VARCHAR(64) UNIQUE,
    item_id VARCHAR(32) REFERENCES public.medical_inventory(id) ON DELETE RESTRICT,
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    patient_astronaut_id VARCHAR(32) REFERENCES public.astronauts(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    authorized_by VARCHAR(64) NOT NULL,
    timestamp_met VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Incidents Table
CREATE TABLE IF NOT EXISTS public.incidents (
    id VARCHAR(64) PRIMARY KEY,
    timestamp VARCHAR(32) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    type VARCHAR(64) NOT NULL,
    "targetAstronautId" VARCHAR(32) REFERENCES public.astronauts(id) ON DELETE CASCADE,
    "targetAstronautName" TEXT NOT NULL,
    summary TEXT NOT NULL,
    "resolutionStatus" VARCHAR(32) NOT NULL,
    "syncStatus" VARCHAR(64) NOT NULL,
    "assignedOfficer" VARCHAR(64) NOT NULL,
    "actionsTaken" JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Audit Logs Table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    sync_id VARCHAR(64) UNIQUE,
    user_officer VARCHAR(64),
    action VARCHAR(64) NOT NULL,
    details TEXT,
    timestamp_met VARCHAR(32),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Recovery Timelines Table
CREATE TABLE IF NOT EXISTS public.recovery_timelines (
    "astronautId" VARCHAR(32) PRIMARY KEY REFERENCES public.astronauts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    protocol TEXT NOT NULL,
    "currentStep" TEXT NOT NULL,
    "progressPercent" INTEGER NOT NULL,
    "projectedFullRecoveryMET" VARCHAR(32) NOT NULL,
    "sleepDebtTarget" TEXT,
    "exercisePermitted" TEXT,
    "circadianLightProfile" TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Cloud Synchronization Transaction Ledger (For non-destructive inventory reconciliation)
CREATE TABLE IF NOT EXISTS public.cloud_sync_ledger (
    id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) UNIQUE NOT NULL,
    item_id VARCHAR(32) REFERENCES public.medical_inventory(id) ON DELETE RESTRICT,
    delta_quantity INTEGER NOT NULL,
    operation_type VARCHAR(32) NOT NULL, -- 'DISPENSE', 'REPLENISH', 'ADJUST'
    authorized_by VARCHAR(64) NOT NULL,
    patient_id VARCHAR(32),
    timestamp_met VARCHAR(32),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Cloud Synchronization Conflicts Table
CREATE TABLE IF NOT EXISTS public.cloud_sync_conflicts (
    id VARCHAR(64) PRIMARY KEY,
    entity_type VARCHAR(32) NOT NULL,
    record_id VARCHAR(64) NOT NULL,
    local_payload JSONB NOT NULL,
    cloud_payload JSONB,
    conflict_reason TEXT NOT NULL,
    resolution_status VARCHAR(32) DEFAULT 'UNRESOLVED', -- 'UNRESOLVED', 'RESOLVED_LOCAL', 'RESOLVED_CLOUD', 'RESOLVED_MERGE'
    resolved_by VARCHAR(64),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance Indices
CREATE INDEX IF NOT EXISTS idx_supabase_telemetry_ast_time ON public.telemetry_history (astronaut_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_supabase_telemetry_packet ON public.telemetry_history (packet_id);
CREATE INDEX IF NOT EXISTS idx_supabase_health_alerts_ast ON public.health_alerts (astronaut_id, status);
CREATE INDEX IF NOT EXISTS idx_supabase_incidents_status ON public.incidents ("syncStatus");
CREATE INDEX IF NOT EXISTS idx_supabase_dispensations_item ON public.inventory_dispensations (item_id);
CREATE INDEX IF NOT EXISTS idx_supabase_dispensations_patient ON public.inventory_dispensations (patient_astronaut_id);
CREATE INDEX IF NOT EXISTS idx_supabase_conflicts_status ON public.cloud_sync_conflicts (resolution_status);
CREATE INDEX IF NOT EXISTS idx_supabase_ledger_item ON public.cloud_sync_ledger (item_id, created_at);

