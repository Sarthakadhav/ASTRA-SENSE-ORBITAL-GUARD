# ASTRA SENSE – ORBITAL GUARD
# PHASE 3: PRODUCTION DEPLOYMENT & OPERATIONS GUIDE

**Author:** Principal DevOps & Infrastructure Engineer  
**Project:** ASTRA SENSE – ORBITAL GUARD  
**Date:** 2026-11-14  

---

## 1. System Architecture & Prerequisites

ASTRA SENSE – ORBITAL GUARD is architected for dual-environment deployment:
1. **Local Flight Operational Deck (Offline-First):**
   - Python 3.10+ (FastAPI, Uvicorn, SQLite 3 in WAL mode).
   - Node.js 18+ & npm for React 19 / Vite 6 frontend.
   - Zero physical hardware, ESP32, Arduino, or MQTT brokers required.
2. **Cloud Replication Destination (Delay-Tolerant):**
   - Supabase PostgreSQL instance with PostgREST.
   - Row Level Security (RLS) enabled on all 10 tables.
   - Stored procedures and timestamp triggers active.

---

## 2. Environment Configuration

### Backend Configuration (`backend/.env`)
Copy `backend/.env.example` to `backend/.env` (never commit `backend/.env` to source control):
```env
ENVIRONMENT=flight_simulation
HOST=0.0.0.0
PORT=8000
DEBUG=False

DATABASE_URL=sqlite:///./orbital_guard.db

# Supabase Cloud Replication Configuration
SUPABASE_URL=https://<your-project-id>.supabase.co
SUPABASE_SECRET_KEY=sb_secret_your_secret_key_here
SUPABASE_PUBLISHABLE_KEY=your_publishable_anon_key_here

# Outbox Engine Parameters
SUPABASE_SYNC_ENABLED=True
SUPABASE_SYNC_INTERVAL_SECONDS=10
SUPABASE_SYNC_BATCH_SIZE=50
SUPABASE_MAX_RETRIES=5

# Deep Space Network Simulation Parameters
DSN_LATENCY_SECONDS=862
DEFAULT_MET_DAYS=142
```

---

## 3. Deployment Steps

### Step 1: Backend Installation & Initialization
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run initial database initialization and seed
python -m app.database.init_db

# Run database optimization and checkpoint
python ../scripts/optimize_database.py
```

### Step 2: Supabase Schema Migration (Cloud Setup)
If setting up a fresh cloud instance:
1. Open the Supabase SQL Editor.
2. Execute the version-controlled migrations in exact sequence:
   - `supabase/migrations/00001_initial_schema.sql`
   - `supabase/migrations/00002_row_level_security.sql`
   - `supabase/migrations/00003_reconciliation_and_triggers.sql`
3. Verify that all 10 tables, 2 functions, and 3 triggers are present.

### Step 3: Operational Backfill
```bash
# Run one-time backfill of operational records
python scripts/migrate_sqlite_to_supabase.py
```

### Step 4: Frontend Production Build
```bash
# In the project root
npm install
npm run build
```

### Step 5: Starting the Production Services
```bash
# Start FastAPI backend server
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# In a separate terminal, serve the frontend production build
npm run preview -- --port 5173
```

---

## 4. Operational Maintenance & Monitoring

1. **Outbox Synchronization Drain:**
   - Monitor outbox state via `GET /api/v1/sync/status` and `GET /api/v1/sync/metrics`.
   - In case of network disconnection, outbox accumulates events in `PENDING` state and drains automatically upon reconnection.
2. **Database WAL Checkpointing:**
   - Execute periodic WAL truncation via `python scripts/optimize_database.py` or trigger `checkpoint_wal(mode='TRUNCATE')`.
3. **Secret Security Audit:**
   - Run `python scripts/scan_secrets.py` prior to any code deployment or Git push.

---

## 5. Rollback & Disaster Recovery

- In the event of local database failure, restore from the physical pre-migration backup located at:
  `backend/backups/orbital_guard_pre_migration_*.db`.
- The local operational database is fully autonomous: if Supabase becomes unreachable, local flight monitoring, telemetry, inventory dispensations, and alerts continue with 100% functionality.
