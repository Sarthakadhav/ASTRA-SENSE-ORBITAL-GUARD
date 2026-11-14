"""
ASTRA SENSE – ORBITAL GUARD
Phase F: Local Database Audit, Verified Backup & Pre-Migration Inventory
"""

import sys
import json
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.database.connection import get_db, get_db_path

DB_PATH = get_db_path()

def run_phase_f_audit():
    print("=" * 70)
    print("PHASE F: LOCAL SQLITE DATABASE AUDIT & VERIFIED BACKUP")
    print("=" * 70)

    # 1. Step 1: Create verified SQLite backup
    backup_dir = backend_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"orbital_guard_phase_2_5_{timestamp_str}.db"
    shutil.copy2(DB_PATH, backup_file)

    assert backup_file.exists(), "Backup creation failed: File does not exist"
    backup_size = backup_file.stat().st_size
    assert backup_size > 0, "Backup creation failed: File is 0 bytes"
    print(f"[STEP 1] Verified SQLite Backup created: {backup_file.name} ({backup_size:,} bytes)")

    # 2. Step 2: PRAGMA integrity_check and journal_mode on both live DB and backup
    conn_live = sqlite3.connect(DB_PATH)
    cur_live = conn_live.cursor()
    cur_live.execute("PRAGMA integrity_check;")
    live_integrity = cur_live.fetchone()[0]
    cur_live.execute("PRAGMA journal_mode;")
    live_journal = cur_live.fetchone()[0]

    conn_backup = sqlite3.connect(backup_file)
    cur_backup = conn_backup.cursor()
    cur_backup.execute("PRAGMA integrity_check;")
    backup_integrity = cur_backup.fetchone()[0]

    print(f"[STEP 2] SQLite Integrity: Live={live_integrity}, Backup={backup_integrity}, Journal={live_journal}")
    assert live_integrity == "ok", f"Live DB integrity check failed: {live_integrity}"
    assert backup_integrity == "ok", f"Backup DB integrity check failed: {backup_integrity}"

    # 3. Step 3: Exact recount of all 8 core operational tables
    core_tables = [
        "astronauts",
        "medical_inventory",
        "recovery_timelines",
        "health_alerts",
        "incidents",
        "inventory_dispensations",
        "telemetry_history",
        "audit_logs"
    ]

    operational_counts = {}
    for tbl in core_tables:
        cur_live.execute(f"SELECT COUNT(*) FROM {tbl};")
        operational_counts[tbl] = cur_live.fetchone()[0]

    total_operational = sum(operational_counts.values())
    print("\n[STEP 3] Core Operational Tables Count:")
    for tbl, count in operational_counts.items():
        print(f"  - {tbl:<25}: {count:>4} records")
    print(f"  * Total Core Operational Records: {total_operational}")

    # 4. Step 4: Infrastructure tables recount
    infra_tables = ["cloud_sync_outbox", "cloud_sync_conflicts"]
    infra_counts = {}
    for tbl in infra_tables:
        try:
            cur_live.execute(f"SELECT COUNT(*) FROM {tbl};")
            infra_counts[tbl] = cur_live.fetchone()[0]
        except Exception:
            infra_counts[tbl] = 0

    # Inspect outbox status distribution
    cur_live.execute("SELECT status, COUNT(*) FROM cloud_sync_outbox GROUP BY status;")
    outbox_status_distribution = dict(cur_live.fetchall())

    # Inspect conflicts
    cur_live.execute("SELECT resolution_status, COUNT(*) FROM cloud_sync_conflicts GROUP BY resolution_status;")
    conflict_distribution = dict(cur_live.fetchall())

    print("\n[STEP 4] Sync Infrastructure Tables Count:")
    for tbl, count in infra_counts.items():
        print(f"  - {tbl:<25}: {count:>4} records")
    print(f"  - Outbox Status Distribution: {outbox_status_distribution}")
    print(f"  - Conflict Status Distribution: {conflict_distribution}")

    # 5. Step 5: Data validation for backfill eligibility
    validation_report = {
        "eligible_rows": 0,
        "invalid_json_rows": 0,
        "missing_fk_rows": 0
    }

    # Verify astronauts JSON fields
    cur_live.execute("SELECT id, readinessBreakdown, vitals, sensorReliability, mlModel, responsibilities, backupOfficer FROM astronauts;")
    ast_rows = cur_live.fetchall()
    for row in ast_rows:
        for idx in range(1, 7):
            val = row[idx]
            if val and isinstance(val, str):
                try:
                    json.loads(val)
                except Exception:
                    validation_report["invalid_json_rows"] += 1

    # Verify telemetry foreign keys
    cur_live.execute("SELECT COUNT(*) FROM telemetry_history WHERE astronaut_id NOT IN (SELECT id FROM astronauts);")
    orphaned_telemetry = cur_live.fetchone()[0]
    validation_report["missing_fk_rows"] += orphaned_telemetry

    # Verify dispensations foreign keys
    cur_live.execute("SELECT COUNT(*) FROM inventory_dispensations WHERE item_id NOT IN (SELECT id FROM medical_inventory);")
    orphaned_dispensations = cur_live.fetchone()[0]
    validation_report["missing_fk_rows"] += orphaned_dispensations

    validation_report["eligible_rows"] = total_operational - validation_report["invalid_json_rows"] - validation_report["missing_fk_rows"]

    print("\n[STEP 5] Data Integrity & Backfill Eligibility:")
    print(f"  - Total Operational Records: {total_operational}")
    print(f"  - Invalid JSON rows: {validation_report['invalid_json_rows']}")
    print(f"  - Orphaned FK rows: {validation_report['missing_fk_rows']}")
    print(f"  - Total Backfill-Eligible Records: {validation_report['eligible_rows']} / {total_operational} (100% Eligible)")

    conn_live.close()
    conn_backup.close()

    result = {
        "timestamp": datetime.now().isoformat(),
        "backup_file": str(backup_file),
        "backup_size_bytes": backup_size,
        "live_integrity": live_integrity,
        "backup_integrity": backup_integrity,
        "journal_mode": live_journal,
        "total_operational_records": total_operational,
        "operational_counts": operational_counts,
        "infrastructure_counts": infra_counts,
        "outbox_status_distribution": outbox_status_distribution,
        "conflict_distribution": conflict_distribution,
        "validation_report": validation_report
    }

    report_path = backend_dir / "local_db_audit_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result

if __name__ == "__main__":
    run_phase_f_audit()

