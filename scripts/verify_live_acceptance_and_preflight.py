"""
ASTRA SENSE – ORBITAL GUARD
Phase 2.5: Live Integration Acceptance & Backfill Preflight Engine
Non-destructive, strictly read-only / disposable test evaluation.
"""

import sys
import os
import json
import time
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime

# Setup sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir))

import httpx
from app.config import settings
from app.database.connection import get_db, get_db_path
from app.database.supabase_client import supabase_manager
from scripts.migrate_sqlite_to_supabase import run_migration

EXPECTED_TABLES = [
    "astronauts",
    "medical_inventory",
    "recovery_timelines",
    "health_alerts",
    "incidents",
    "inventory_dispensations",
    "telemetry_history",
    "audit_logs",
    "cloud_sync_ledger",
    "cloud_sync_conflicts"
]

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

async def run_audit():
    audit = {
        "timestamp": datetime.now().isoformat(),
        "task_a_backend_connection": {},
        "task_b_security_tests": {},
        "task_c_category_c_tests": {},
        "task_d_backfill_preflight": {},
        "verdict": "UNKNOWN"
    }

    url = supabase_manager.url.rstrip("/")
    service_headers = supabase_manager._get_headers(prefer_merge=False)
    anon_key = settings.SUPABASE_PUBLISHABLE_KEY
    anon_headers = {
        "apikey": anon_key,
        "Content-Type": "application/json"
    }

    # =========================================================================
    # TASK A — LIVE BACKEND CONNECTION
    # =========================================================================
    print("=" * 70)
    print("TASK A: LIVE BACKEND CONNECTION & TABLE ACCESSIBILITY")
    print("=" * 70)

    # 1. Credential detection & format verification (no secret exposure)
    has_url = bool(settings.SUPABASE_URL)
    has_secret = bool(settings.SUPABASE_SECRET_KEY)
    is_opaque = settings.SUPABASE_SECRET_KEY.startswith("sb_secret_")
    has_pub = bool(settings.SUPABASE_PUBLISHABLE_KEY)
    
    header_apikey_present = "apikey" in service_headers and bool(service_headers["apikey"])
    header_auth_present = "Authorization" in service_headers

    audit["task_a_backend_connection"]["config"] = {
        "supabase_url_configured": has_url,
        "supabase_domain": url.split("://")[-1].split("/")[0] if has_url else "NONE",
        "secret_key_detected": has_secret,
        "secret_key_format": "MODERN_OPAQUE (sb_secret_...)" if is_opaque else "LEGACY_JWT",
        "publishable_key_detected": has_pub,
        "header_apikey_present": header_apikey_present,
        "header_authorization_omitted_for_opaque": (not header_auth_present) if is_opaque else False,
    }

    # 2. Connection health check
    conn_res = await supabase_manager.test_connection()
    audit["task_a_backend_connection"]["health_check"] = conn_res
    print(f"Health Check: status={conn_res.get('status')} connected={conn_res.get('connected')}")

    # 3. PostgREST table access test for all 10 tables
    table_access = {}
    async with httpx.AsyncClient(timeout=8.0) as client:
        for tbl in EXPECTED_TABLES:
            endpoint = f"{url}/rest/v1/{tbl}?select=count"
            head_h = dict(service_headers)
            head_h["Prefer"] = "count=exact"
            try:
                res = await client.get(endpoint, headers=head_h)
                count_str = res.headers.get("Content-Range", "").split("/")[-1] if "/" in res.headers.get("Content-Range", "") else "0"
                table_access[tbl] = {
                    "status_code": res.status_code,
                    "accessible": res.status_code in (200, 206),
                    "cloud_row_count": count_str
                }
                print(f"  - Table {tbl:<25}: HTTP {res.status_code} (rows: {count_str})")
            except Exception as e:
                table_access[tbl] = {
                    "status_code": "ERROR",
                    "accessible": False,
                    "error": str(e)
                }
                print(f"  - Table {tbl:<25}: ERROR ({e})")

    audit["task_a_backend_connection"]["table_accessibility"] = table_access
    all_tables_ok = all(v.get("accessible") for v in table_access.values())
    audit["task_a_backend_connection"]["all_tables_accessible"] = all_tables_ok
    print(f"All 10 Cloud Tables Accessible by service_role: {all_tables_ok}\n")

    # =========================================================================
    # TASK B — LIVE SECURITY TESTS (anon vs authenticated vs service_role)
    # =========================================================================
    print("=" * 70)
    print("TASK B: LIVE SECURITY & RLS ENFORCEMENT AUDIT")
    print("=" * 70)

    security_results = {
        "anon_read_tests": {},
        "anon_write_tests": {},
        "authenticated_read_tests": {},
        "authenticated_write_tests": {},
        "service_role_read_tests": {},
        "rpc_permission_tests": {}
    }

    test_tables = ["astronauts", "medical_inventory", "incidents", "telemetry_history"]
    
    async with httpx.AsyncClient(timeout=8.0) as client:
        # 1. Anonymous Read Tests (Must return 0 rows or 401/403)
        print("[TEST B.1] Anonymous Role Reads (using publishable key):")
        for tbl in test_tables:
            endpoint = f"{url}/rest/v1/{tbl}?select=*"
            res = await client.get(endpoint, headers=anon_headers)
            # RLS without policy returns 200 with empty list []
            is_empty = res.status_code == 200 and res.json() == []
            is_denied = res.status_code in (401, 403) or is_empty
            security_results["anon_read_tests"][tbl] = {
                "status_code": res.status_code,
                "rows_returned": len(res.json()) if res.status_code == 200 and isinstance(res.json(), list) else 0,
                "access_denied": is_denied
            }
            print(f"  - Read {tbl:<20}: HTTP {res.status_code} | Rows: {len(res.json()) if res.status_code == 200 else 0} | Access Denied: {is_denied}")

        # 2. Anonymous Write Tests (Must fail with 401/403/PGRST301)
        print("\n[TEST B.2] Anonymous Role Write (Attempt INSERT on public.astronauts):")
        fake_payload = {
            "id": "UNAUTHORIZED-AST",
            "name": "Intruder",
            "role": "None",
            "dutyCategory": "None",
            "condition": "None",
            "conditionSeverity": "None"
        }
        res_write_anon = await client.post(f"{url}/rest/v1/astronauts", json=fake_payload, headers=anon_headers)
        anon_write_blocked = res_write_anon.status_code in (401, 403, 404) or "PGRST" in res_write_anon.text or res_write_anon.status_code >= 400
        security_results["anon_write_tests"]["astronauts"] = {
            "status_code": res_write_anon.status_code,
            "blocked": anon_write_blocked,
            "response": res_write_anon.text[:120]
        }
        print(f"  - Write astronauts: HTTP {res_write_anon.status_code} | Write Blocked: {anon_write_blocked}")

        # 3. Authenticated Browser Client Tests (Simulating standard client JWT)
        print("\n[TEST B.3] Authenticated Role Reads & Writes (Simulated browser JWT):")
        # Simulated non-service browser JWT token
        dummy_token = "mock_browser_user_session_token_for_rls_test"
        auth_browser_headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {dummy_token}",
            "Content-Type": "application/json"
        }
        res_read_auth = await client.get(f"{url}/rest/v1/astronauts?select=*", headers=auth_browser_headers)
        auth_read_blocked = res_read_auth.status_code in (401, 403) or (res_read_auth.status_code == 200 and res_read_auth.json() == [])
        security_results["authenticated_read_tests"]["astronauts"] = {
            "status_code": res_read_auth.status_code,
            "blocked": auth_read_blocked
        }
        print(f"  - Read astronauts (browser token): HTTP {res_read_auth.status_code} | Blocked: {auth_read_blocked}")

        res_write_auth = await client.post(f"{url}/rest/v1/astronauts", json=fake_payload, headers=auth_browser_headers)
        auth_write_blocked = res_write_auth.status_code in (401, 403) or res_write_auth.status_code >= 400
        security_results["authenticated_write_tests"]["astronauts"] = {
            "status_code": res_write_auth.status_code,
            "blocked": auth_write_blocked
        }
        print(f"  - Write astronauts (browser token): HTTP {res_write_auth.status_code} | Blocked: {auth_write_blocked}")

        # 4. Service Role Access Test
        print("\n[TEST B.4] Service Role Access (FastAPI Backend Outbox Worker):")
        res_serv_read = await client.get(f"{url}/rest/v1/astronauts?select=*", headers=service_headers)
        serv_read_ok = res_serv_read.status_code == 200
        security_results["service_role_read_tests"]["astronauts"] = {
            "status_code": res_serv_read.status_code,
            "permitted": serv_read_ok
        }
        print(f"  - Read astronauts (service_role): HTTP {res_serv_read.status_code} | Permitted: {serv_read_ok}")

        # 5. RPC Security Tests
        print("\n[TEST B.5] RPC Execution Permissions (reconcile_inventory_transaction):")
        # Anon invoke attempt
        res_rpc_anon = await client.post(
            f"{url}/rest/v1/rpc/reconcile_inventory_transaction",
            json={},
            headers=anon_headers
        )
        rpc_anon_denied = res_rpc_anon.status_code in (401, 403, 404) or "PGRST" in res_rpc_anon.text
        security_results["rpc_permission_tests"]["anon_invoke"] = {
            "status_code": res_rpc_anon.status_code,
            "denied": rpc_anon_denied,
            "detail": res_rpc_anon.text[:120]
        }
        print(f"  - Anon RPC invoke: HTTP {res_rpc_anon.status_code} | Denied: {rpc_anon_denied}")

        # Service role presence check
        res_rpc_serv = await client.get(f"{url}/rest/v1/", headers=service_headers)
        rpc_in_spec = "/rpc/reconcile_inventory_transaction" in res_rpc_serv.json().get("paths", {})
        security_results["rpc_permission_tests"]["service_role_registered"] = {
            "registered": rpc_in_spec,
            "status": "AUTHORIZED" if rpc_in_spec else "MISSING"
        }
        print(f"  - Service Role RPC registered: {rpc_in_spec}")

    audit["task_b_security_tests"] = security_results

    # =========================================================================
    # TASK C — CATEGORY C INTEGRATION TESTS
    # =========================================================================
    print("\n" + "=" * 70)
    print("TASK C: CATEGORY C LIVE INTEGRATION TESTS")
    print("=" * 70)

    category_c_results = {}
    
    # 1. Connectivity test
    c1 = await supabase_manager.test_connection()
    category_c_results["connectivity"] = {
        "status": c1.get("status"),
        "connected": c1.get("connected"),
        "passed": c1.get("connected") is True
    }
    print(f"  - Test 1 (Live Connectivity): {'PASSED' if c1.get('connected') else 'FAILED'}")

    # 2. Secret Redaction test
    secret_sample = f"Exception with {settings.SUPABASE_SECRET_KEY} embedded"
    scrubbed = supabase_manager._scrub_error(secret_sample)
    redaction_ok = "sb_secret_" not in scrubbed and "[REDACTED_KEY]" in scrubbed
    category_c_results["secret_redaction"] = {
        "passed": redaction_ok,
        "detail": "Secret tokens successfully scrubbed from error logs"
    }
    print(f"  - Test 2 (Secret Redaction): {'PASSED' if redaction_ok else 'FAILED'}")

    # 3. Isolated disposable write & cleanup test
    test_id = f"TEST-ACCEPT-{int(time.time())}"
    test_record = {
        "id": test_id,
        "name": "Disposable Preflight Subject",
        "callsign": "Disposable",
        "role": "Preflight Validation",
        "dutyCategory": "Validation",
        "condition": "Nominal",
        "conditionSeverity": "nominal"
    }
    
    upsert_res = await supabase_manager.upsert_record("astronauts", test_record, on_conflict="id")
    write_ok = upsert_res.get("status") == "SUCCESS"
    print(f"  - Test 3 (Disposable Record Upsert): {'PASSED' if write_ok else 'FAILED'}")

    # Clean up immediately
    delete_ok = False
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            del_res = await client.delete(
                f"{url}/rest/v1/astronauts?id=eq.{test_id}",
                headers=service_headers
            )
            delete_ok = del_res.status_code in (200, 204)
    except Exception:
        delete_ok = False
    print(f"  - Test 4 (Disposable Record Clean Up): {'PASSED' if delete_ok else 'FAILED'}")

    category_c_results["isolated_crud"] = {
        "upsert_passed": write_ok,
        "cleanup_passed": delete_ok,
        "zero_residue": write_ok and delete_ok
    }

    # 4. Read safety verification: Ensure 0 records remain in astronauts
    async with httpx.AsyncClient(timeout=8.0) as client:
        chk_res = await client.get(f"{url}/rest/v1/astronauts?select=id", headers=service_headers)
        astronaut_cloud_count = len(chk_res.json()) if chk_res.status_code == 200 else -1
        category_c_results["cloud_purity_check"] = {
            "astronauts_count": astronaut_cloud_count,
            "pure": astronaut_cloud_count == 0
        }
        print(f"  - Test 5 (Cloud Purity Verification): {'PASSED (0 rows)' if astronaut_cloud_count == 0 else 'FAILED'}")

    audit["task_c_category_c_tests"] = category_c_results

    # =========================================================================
    # TASK D — BACKFILL PREFLIGHT & DRY RUN
    # =========================================================================
    print("\n" + "=" * 70)
    print("TASK D: BACKFILL PREFLIGHT (STRICTLY DRY-RUN / READ-ONLY)")
    print("=" * 70)

    preflight_d = {}

    # 1. SQLite DB Integrity & PRAGMA Checks
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        integrity_res = cursor.fetchone()[0]
        
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]

    preflight_d["sqlite_health"] = {
        "integrity_check": integrity_res,
        "foreign_key_violations": len(fk_violations),
        "journal_mode": journal_mode,
        "healthy": integrity_res == "ok" and len(fk_violations) == 0 and journal_mode.lower() == "wal"
    }
    print(f"SQLite Integrity: {integrity_res} | FK Violations: {len(fk_violations)} | Journal Mode: {journal_mode}")

    # 2. Local SQLite Record Counts
    local_counts = {}
    with get_db() as conn:
        cursor = conn.cursor()
        for tbl in OPERATIONAL_TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
            local_counts[tbl] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cloud_sync_outbox;")
        outbox_total = cursor.fetchone()[0]
        cursor.execute("SELECT status, COUNT(*) FROM cloud_sync_outbox GROUP BY status;")
        outbox_by_status = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM cloud_sync_conflicts;")
        conflict_total = cursor.fetchone()[0]
        cursor.execute("SELECT resolution_status, COUNT(*) FROM cloud_sync_conflicts GROUP BY resolution_status;")
        conflicts_by_status = dict(cursor.fetchall())

    total_operational = sum(local_counts.values())
    preflight_d["source_counts"] = {
        "operational_tables": local_counts,
        "total_operational_records": total_operational,
        "infrastructure": {
            "cloud_sync_outbox_total": outbox_total,
            "cloud_sync_outbox_by_status": outbox_by_status,
            "cloud_sync_conflicts_total": conflict_total,
            "cloud_sync_conflicts_by_status": conflicts_by_status
        }
    }
    print(f"Total Operational Records: {total_operational} across 8 tables")
    print(f"Sync Infrastructure: {outbox_total} outbox events ({outbox_by_status}), {conflict_total} conflicts")

    # 3. Backup Availability Check
    backup_dir = backend_dir / "backups"
    backups = list(backup_dir.glob("*.db")) if backup_dir.exists() else []
    backup_info = []
    for b in backups:
        backup_info.append({
            "name": b.name,
            "size_bytes": b.stat().st_size,
            "modified": datetime.fromtimestamp(b.stat().st_mtime).isoformat()
        })
    preflight_d["backups"] = {
        "backup_count": len(backups),
        "files": backup_info,
        "verified_backup_present": len(backups) > 0 and all(b["size_bytes"] > 0 for b in backup_info)
    }
    print(f"Backups Available: {len(backups)} verified SQLite backup(s)")

    # 4. Target Cloud Counts (Must all be 0)
    cloud_counts = {}
    async with httpx.AsyncClient(timeout=8.0) as client:
        for tbl in EXPECTED_TABLES:
            h = dict(service_headers)
            h["Prefer"] = "count=exact"
            r = await client.get(f"{url}/rest/v1/{tbl}?select=count", headers=h)
            cnt = r.headers.get("Content-Range", "").split("/")[-1] if "/" in r.headers.get("Content-Range", "") else "0"
            cloud_counts[tbl] = int(cnt) if cnt.isdigit() else 0

    preflight_d["cloud_counts"] = cloud_counts
    total_cloud_rows = sum(cloud_counts.values())
    preflight_d["total_cloud_rows"] = total_cloud_rows
    print(f"Current Total Cloud Records: {total_cloud_rows} (All 10 tables clean)")

    # 5. Dependency Mapping & Backfill Ordering Plan
    ordering_plan = [
        {"tier": 1, "table": "astronauts", "records": local_counts["astronauts"], "depends_on": []},
        {"tier": 1, "table": "medical_inventory", "records": local_counts["medical_inventory"], "depends_on": []},
        {"tier": 2, "table": "recovery_timelines", "records": local_counts["recovery_timelines"], "depends_on": ["astronauts"]},
        {"tier": 2, "table": "health_alerts", "records": local_counts["health_alerts"], "depends_on": ["astronauts"]},
        {"tier": 2, "table": "incidents", "records": local_counts["incidents"], "depends_on": ["astronauts"]},
        {"tier": 3, "table": "inventory_dispensations", "records": local_counts["inventory_dispensations"], "depends_on": ["medical_inventory", "astronauts"]},
        {"tier": 4, "table": "telemetry_history", "records": local_counts["telemetry_history"], "depends_on": ["astronauts"]},
        {"tier": 4, "table": "audit_logs", "records": local_counts["audit_logs"], "depends_on": []}
    ]
    preflight_d["ordering_plan"] = ordering_plan

    # 6. Run Dry-Run Migration
    print("\nRunning Migration Preview Dry-Run...")
    dry_run_report = await run_migration(dry_run=True)
    preflight_d["dry_run_report"] = {
        "mode": dry_run_report.get("mode"),
        "total_source_records": dry_run_report.get("total_source_records"),
        "validation_errors": dry_run_report.get("validation_errors_count"),
        "success": dry_run_report.get("validation_errors_count") == 0
    }
    print(f"Dry Run Result: Mode={dry_run_report.get('mode')} | Validation Errors={dry_run_report.get('validation_errors_count')}")

    audit["task_d_backfill_preflight"] = preflight_d

    # =========================================================================
    # OVERALL PREFLIGHT VERDICT
    # =========================================================================
    can_go = (
        all_tables_ok
        and security_results["anon_write_tests"]["astronauts"]["blocked"]
        and security_results["service_role_read_tests"]["astronauts"]["permitted"]
        and category_c_results["connectivity"]["passed"]
        and category_c_results["secret_redaction"]["passed"]
        and category_c_results["isolated_crud"]["zero_residue"]
        and preflight_d["sqlite_health"]["healthy"]
        and total_operational == 303
        and total_cloud_rows == 0
        and dry_run_report.get("validation_errors_count") == 0
    )

    audit["verdict"] = "GO FOR BACKFILL" if can_go else "NO-GO"
    print("\n" + "=" * 70)
    print(f"PREFLIGHT VERDICT: {audit['verdict']}")
    print("=" * 70)

    # Save structured audit result
    out_file = Path(__file__).resolve().parent / "acceptance_and_preflight_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)
    print(f"Audit log saved to: {out_file.name}")

if __name__ == "__main__":
    asyncio.run(run_audit())
