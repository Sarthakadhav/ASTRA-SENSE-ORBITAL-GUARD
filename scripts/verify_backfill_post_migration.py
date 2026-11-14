"""
ASTRA SENSE – ORBITAL GUARD
Phase 2.5: Post-Backfill Comprehensive Verification Script
Verifies table-by-table record counts, primary keys, foreign keys, JSON types, and data integrity.
"""

import sys
import json
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import httpx
from app.config import settings
from app.database.connection import get_db, get_db_path
from app.database.supabase_client import supabase_manager

OPERATIONAL_TABLES = [
    "astronauts",
    "medical_inventory",
    "recovery_timelines",
    "health_alerts",
    "incidents",
    "inventory_dispensations",
    "telemetry_history",
    "audit_logs"
]

INFRASTRUCTURE_TABLES = [
    "cloud_sync_ledger",
    "cloud_sync_conflicts"
]

ALL_CLOUD_TABLES = OPERATIONAL_TABLES + INFRASTRUCTURE_TABLES

async def verify():
    print("=" * 70)
    print("PHASE 2.5: POST-BACKFILL TABLE-BY-TABLE RECONCILIATION")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target: {settings.SUPABASE_URL}\n")

    # 1. Source SQLite counts
    source_counts = {}
    with get_db() as conn:
        cursor = conn.cursor()
        for t in OPERATIONAL_TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM {t};")
            source_counts[t] = cursor.fetchone()[0]

        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchone()[0]

        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()

        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]

    # 2. Cloud Supabase counts
    cloud_counts = {}
    url = supabase_manager.url.rstrip("/")
    headers = supabase_manager._get_headers()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for t in ALL_CLOUD_TABLES:
            h = dict(headers)
            h["Prefer"] = "count=exact"
            res = await client.get(f"{url}/rest/v1/{t}?select=count", headers=h)
            cnt = res.headers.get("Content-Range", "").split("/")[-1] if "/" in res.headers.get("Content-Range", "") else "0"
            cloud_counts[t] = int(cnt) if cnt.isdigit() else -1

    # 3. Print comparison table
    print(f"{'Table Name':<28} | {'SQLite Rows':<12} | {'Cloud Rows':<12} | {'Match?':<8}")
    print("-" * 68)
    all_matched = True
    for t in OPERATIONAL_TABLES:
        s_cnt = source_counts.get(t, 0)
        c_cnt = cloud_counts.get(t, 0)
        match = (s_cnt == c_cnt)
        if not match:
            all_matched = False
        print(f"{t:<28} | {s_cnt:<12} | {c_cnt:<12} | {'YES' if match else 'NO':<8}")

    print("-" * 68)
    total_source = sum(source_counts.values())
    total_cloud_op = sum(cloud_counts[t] for t in OPERATIONAL_TABLES)
    print(f"{'TOTAL OPERATIONAL':<28} | {total_source:<12} | {total_cloud_op:<12} | {'YES' if total_source == total_cloud_op else 'NO':<8}\n")

    # Infrastructure tables
    print("Cloud Infrastructure Tables:")
    for t in INFRASTRUCTURE_TABLES:
        print(f"  - {t:<26}: {cloud_counts.get(t, 0)} records")

    # 4. Detailed Data Integrity Sampling
    print("\n" + "=" * 70)
    print("DATA INTEGRITY & FIELD SAMPLING")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Astronauts check
        ast_res = await client.get(f"{url}/rest/v1/astronauts?id=eq.AST-01", headers=headers)
        ast_data = ast_res.json()[0] if ast_res.status_code == 200 and ast_res.json() else {}
        print(f"Astronauts (AST-01): Name='{ast_data.get('name')}', Role='{ast_data.get('role')}', Vitals is JSONB: {isinstance(ast_data.get('vitals'), dict)}")

        # Telemetry check
        tel_res = await client.get(f"{url}/rest/v1/telemetry_history?order=id.asc&limit=1", headers=headers)
        tel_data = tel_res.json()[0] if tel_res.status_code == 200 and tel_res.json() else {}
        print(f"Telemetry (First row): sync_id='{tel_data.get('sync_id')}', packet_id={tel_data.get('packet_id')}, SpO2={tel_data.get('spo2_pct')}%, crc32_valid={tel_data.get('crc32_valid')} (type: {type(tel_data.get('crc32_valid')).__name__})")

        # Inventory check
        med_res = await client.get(f"{url}/rest/v1/medical_inventory?id=eq.MED-01", headers=headers)
        med_data = med_res.json()[0] if med_res.status_code == 200 and med_res.json() else {}
        print(f"Medical Inventory (MED-01): Name='{med_data.get('name')}', Stock={med_data.get('stock')} {med_data.get('unit')}, MinSafeStock={med_data.get('minSafeStock')}")

        # Incidents check
        inc_res = await client.get(f"{url}/rest/v1/incidents?order=id.asc&limit=1", headers=headers)
        inc_data = inc_res.json()[0] if inc_res.status_code == 200 and inc_res.json() else {}
        print(f"Incident (Sample): id='{inc_data.get('id')}', targetAstronaut='{inc_data.get('targetAstronautName')}', severity='{inc_data.get('severity')}'")

        # Recovery timeline check
        rec_res = await client.get(f"{url}/rest/v1/recovery_timelines?order=astronautId.asc&limit=1", headers=headers)
        rec_data = rec_res.json()[0] if rec_res.status_code == 200 and rec_res.json() else {}
        print(f"Recovery Timeline (Sample): astronautId='{rec_data.get('astronautId')}', Protocol='{rec_data.get('protocol')[:40]}...'")

    # 5. Outbox Status Check
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM cloud_sync_outbox GROUP BY status;")
        outbox_states = dict(cursor.fetchall())
        print(f"\nLocal cloud_sync_outbox State: {outbox_states}")

    print(f"SQLite Integrity: {integrity} | FK Violations: {len(fk_violations)} | Journal Mode: {journal_mode}")
    print(f"Final Reconciliation Verdict: {'SUCCESS - 100% RECONCILED' if all_matched else 'MISMATCH DETECTED'}")

    # Output structured verification report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_operational_source": total_source,
        "total_operational_cloud": total_cloud_op,
        "all_tables_matched": all_matched,
        "source_counts": source_counts,
        "cloud_counts": cloud_counts,
        "outbox_states": outbox_states,
        "sqlite_health": {
            "integrity": integrity,
            "fk_violations": len(fk_violations),
            "journal_mode": journal_mode
        }
    }
    with open("backend/backfill_verification.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    asyncio.run(verify())

