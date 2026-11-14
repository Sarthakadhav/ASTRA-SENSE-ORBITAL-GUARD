# ASTRA SENSE – ORBITAL GUARD
# PHASE 3: RISK REGISTER & MITIGATION MATRIX

**Author:** Principal Cybersecurity Engineer & Aerospace Risk Analyst  
**Project:** ASTRA SENSE – ORBITAL GUARD  
**Date:** 2026-11-14  

---

## 1. Risk Evaluation Matrix

Risks are categorized across Likelihood (L1-L5) and Impact (I1-I5) to establish Severity (Low, Medium, High, Critical).

| Risk ID | Category | Description | Likelihood | Impact | Severity | Primary Mitigation Strategy |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **RSK-01** | Distributed Sync | Sequence collisions on `BIGSERIAL` primary keys during outbox inserts | L2 | I4 | **Medium** | Pop local `id` on append-only tables, rely on `sync_id` for deduplication, and cycle sequences past backfilled boundaries. |
| **RSK-02** | Data Integrity | PostgreSQL `NOT NULL` constraint violations on partial updates via PostgREST | L2 | I4 | **Medium** | Implement `_enrich_payload` to merge delta outbox updates with authoritative local SQLite records. |
| **RSK-03** | Cloud Security | Exposure of modern Supabase opaque keys (`sb_secret_...`) in Git, logs, or UI | L1 | I5 | **Critical** | Automated pre-commit secret scanner (`scripts/scan_secrets.py`), `.gitignore` enforcement, sanitized error scrubber. |
| **RSK-04** | Telemetry Stream | Packet loss, clock drift, or out-of-order arrival in telemetry ingest pipeline | L3 | I3 | **Medium** | Sequence gap detection, duplicate packet filter, and timestamp jitter validation window (<500ms). |
| **RSK-05** | Availability | Unchecked SQLite WAL file growth causing slow checkpointing or disk exhaustion | L2 | I4 | **Medium** | Automatic WAL truncate checkpointing on connection management and dedicated database maintenance script. |
| **RSK-06** | Access Control | Privilege escalation by unauthenticated or student-role users on clinical actions | L2 | I4 | **Medium** | Server-side RBAC validation with token expiration enforcement and audit logging of unauthorized attempts. |
| **RSK-07** | Network Resilience | Prolonged Deep Space Network (DSN) link outage causing outbox buffer overflow | L3 | I3 | **Medium** | Autonomous local-first execution; transactional outbox buffers indefinitely until link restoration with backoff. |

---

## 2. Contingency Procedures

1. **Cloud Gateway Rejection:**
   If Supabase returns HTTP 401/403 or network timeout, the application immediately falls back to `LOCAL_ONLY` mode. Local flight operations (vital telemetry, incident creation, medication dispensations) proceed with zero interruption.
2. **Outbox Dead-Letter Triage:**
   Records failing after `max_retries` transition to `DEAD_LETTER` status. The outbox processor continues servicing healthy records, preventing a single malformed payload from stalling the queue.
3. **Emergency Database Rollback:**
   Physical SQLite snapshots are captured before destructive operations. In case of local database corruption, the pre-migration backup (`backend/backups/orbital_guard_pre_migration_*.db`) is restored.
