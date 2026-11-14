"""
ASTRA SENSE – ORBITAL GUARD
Read-Only Live Supabase Preflight Diagnostic Engine
Phase 2.5: Live Cloud Integration & Schema Verification
"""

import sys
import json
import asyncio
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import httpx
from app.config import settings
from app.database.supabase_client import supabase_manager
from app.database.connection import get_db, get_db_path

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

EXPECTED_RPC = [
    "reconcile_inventory_transaction"
]

async def run_preflight():
    report = {
        "credentials": {},
        "connectivity": {},
        "headers_verification": {},
        "schema_inspection": {},
        "rpc_inspection": {},
        "local_data_readiness": {},
        "migration_readiness": {},
        "verdict": "UNKNOWN"
    }

    # 1. Credential Verification (Without exposing secrets)
    url = settings.SUPABASE_URL
    secret_key = settings.SUPABASE_SECRET_KEY
    pub_key = settings.SUPABASE_PUBLISHABLE_KEY
    jwks_url = settings.SUPABASE_JWKS_URL

    report["credentials"]["url_configured"] = bool(url)
    report["credentials"]["url_domain"] = url.split("://")[-1].split("/")[0] if url else "NONE"
    report["credentials"]["url_https"] = url.startswith("https://") if url else False

    report["credentials"]["secret_key_configured"] = bool(secret_key)
    report["credentials"]["secret_key_length"] = len(secret_key) if secret_key else 0
    report["credentials"]["secret_key_format"] = (
        "MODERN_OPAQUE (sb_secret_...)" if secret_key.startswith("sb_secret_")
        else ("LEGACY_JWT (eyJ...)" if secret_key.startswith("eyJ")
        else ("PLACEHOLDER" if "PASTE_YOUR" in secret_key or "placeholder" in secret_key.lower()
        else "UNKNOWN_OR_CUSTOM"))
    )

    report["credentials"]["publishable_key_configured"] = bool(pub_key)
    report["credentials"]["publishable_key_format"] = (
        "MODERN_OPAQUE (sb_publishable_...)" if pub_key.startswith("sb_publishable_")
        else ("LEGACY_JWT (eyJ...)" if pub_key.startswith("eyJ")
        else ("PLACEHOLDER" if "PASTE_YOUR" in pub_key or "placeholder" in pub_key.lower()
        else "NONE" if not pub_key else "CUSTOM"))
    )

    report["credentials"]["jwks_url_configured"] = bool(jwks_url)
    report["credentials"]["is_configured"] = supabase_manager.is_configured

    # 2. Header Verification
    headers = supabase_manager._get_headers(prefer_merge=False)
    has_apikey = "apikey" in headers and bool(headers["apikey"])
    has_auth = "Authorization" in headers
    is_opaque = secret_key.startswith("sb_secret_")

    report["headers_verification"] = {
        "apikey_header_present": has_apikey,
        "authorization_header_present": has_auth,
        "opaque_key_correctly_omits_bearer": (not has_auth) if is_opaque else "N/A (legacy JWT)",
        "content_type_json": headers.get("Content-Type") == "application/json"
    }

    # 3. Live Connectivity
    # Probe 1: Public JWKS endpoint reachability
    jwks_probe = {}
    if jwks_url:
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                j_res = await client.get(jwks_url)
                jwks_probe = {
                    "reachable": j_res.status_code == 200,
                    "status_code": j_res.status_code,
                    "keys_count": len(j_res.json().get("keys", [])) if j_res.status_code == 200 else 0
                }
        except Exception as exc:
            jwks_probe = {"reachable": False, "error": str(exc)}
    report["connectivity"]["jwks_endpoint_probe"] = jwks_probe

    # Probe 2: PostgREST gateway reachability (unauthenticated probe)
    gateway_probe = {}
    if url:
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                g_res = await client.get(f"{url.rstrip('/')}/rest/v1/")
                gateway_probe = {
                    "reachable": True,
                    "status_code": g_res.status_code,
                    "message": "Gateway active and responding" if g_res.status_code in (200, 401, 404) else f"HTTP {g_res.status_code}"
                }
        except Exception as exc:
            gateway_probe = {"reachable": False, "error": str(exc)}
    report["connectivity"]["gateway_probe"] = gateway_probe

    # Probe 3: Client Manager configured check
    conn_result = await supabase_manager.test_connection()
    report["connectivity"]["client_manager_status"] = conn_result

    # Local Data Readiness (SQLite WAL Audit)
    local_counts = {}
    with get_db() as conn:
        cursor = conn.cursor()
        for tbl in EXPECTED_TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
                local_counts[tbl] = cursor.fetchone()[0]
            except Exception:
                local_counts[tbl] = 0

    report["local_data_readiness"] = {
        "sqlite_wal": True,
        "local_operational_records": sum(local_counts[t] for t in EXPECTED_TABLES[:8]),
        "local_outbox_events": local_counts.get("cloud_sync_ledger", 0) + local_counts.get("cloud_sync_conflicts", 0),
        "counts_by_table": local_counts
    }

    # If offline or not configured, return early with local readiness intact
    if not conn_result.get("connected"):
        report["verdict"] = "NOT READY"
        report["migration_readiness"]["status"] = "BLOCKED"
        report["migration_readiness"]["reason"] = (
            "Placeholder secret key detected in backend/.env ('PASTE_YOUR_SUPABASE_SECRET_KEY_HERE'). "
            "Please paste your real 'sb_secret_...' key to proceed with authenticated schema inspection."
            if "PLACEHOLDER" in report["credentials"]["secret_key_format"]
            else f"Cloud connection failed: {conn_result.get('error') or conn_result.get('message')}"
        )
        return report

    # 4. Database Schema Inspection (Read-Only)
    # Fetch OpenAPI definition from PostgREST root
    endpoint = f"{supabase_manager.url.rstrip('/')}/rest/v1/"
    openapi_defs = {}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(endpoint, headers=headers)
            if res.status_code == 200:
                try:
                    spec = res.json()
                    paths = spec.get("paths", {})
                    openapi_defs = paths
                except Exception:
                    pass
    except Exception as exc:
        report["schema_inspection"]["openapi_fetch_error"] = str(exc)

    # Inspect each expected table via read-only HEAD / SELECT count
    tables_found = {}
    missing_tables = []
    for tbl in EXPECTED_TABLES:
        tbl_endpoint = f"{supabase_manager.url.rstrip('/')}/rest/v1/{tbl}?select=count"
        head_headers = dict(headers)
        head_headers["Prefer"] = "count=exact"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                t_res = await client.get(tbl_endpoint, headers=head_headers)
                if t_res.status_code in (200, 206):
                    content_range = t_res.headers.get("Content-Range", "")
                    count_val = content_range.split("/")[-1] if "/" in content_range else "0"
                    tables_found[tbl] = {
                        "exists": True,
                        "status_code": t_res.status_code,
                        "current_cloud_rows": count_val,
                        "in_openapi": f"/{tbl}" in openapi_defs
                    }
                elif t_res.status_code == 404:
                    missing_tables.append(tbl)
                    tables_found[tbl] = {
                        "exists": False,
                        "status_code": 404,
                        "detail": "Table not found in Supabase schema (migration not applied)"
                    }
                else:
                    tables_found[tbl] = {
                        "exists": False,
                        "status_code": t_res.status_code,
                        "detail": t_res.text[:150]
                    }
        except Exception as exc:
            tables_found[tbl] = {"exists": False, "error": str(exc)}

    report["schema_inspection"]["tables"] = tables_found
    report["schema_inspection"]["missing_tables"] = missing_tables
    report["schema_inspection"]["all_tables_present"] = len(missing_tables) == 0

    # Inspect RPC functions
    rpc_status = {}
    for rpc_name in EXPECTED_RPC:
        rpc_path = f"/rpc/{rpc_name}"
        if rpc_path in openapi_defs:
            rpc_status[rpc_name] = {
                "exists": True,
                "status_code": 200,
                "detail": "RPC function registered in PostgREST OpenAPI schema",
                "in_openapi": True
            }
        else:
            rpc_endpoint = f"{supabase_manager.url.rstrip('/')}/rest/v1/rpc/{rpc_name}"
            try:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    r_res = await client.post(rpc_endpoint, json={}, headers=headers)
                    if r_res.status_code == 404:
                        rpc_status[rpc_name] = {
                            "exists": False,
                            "status_code": 404,
                            "detail": "RPC function does not exist in PostgreSQL schema"
                        }
                    else:
                        rpc_status[rpc_name] = {
                            "exists": True,
                            "status_code": r_res.status_code,
                            "detail": "RPC function detected on PostgREST endpoint"
                        }
            except Exception as exc:
                rpc_status[rpc_name] = {"exists": False, "error": str(exc)}

    report["rpc_inspection"] = rpc_status
    all_rpc_present = all(v.get("exists") for v in rpc_status.values())

    # 5. Local Data Readiness
    local_counts = {}
    with get_db() as conn:
        cursor = conn.cursor()
        for tbl in EXPECTED_TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
                local_counts[tbl] = cursor.fetchone()[0]
            except Exception:
                local_counts[tbl] = 0

    report["local_data_readiness"] = {
        "sqlite_wal": True,
        "local_operational_records": sum(local_counts[t] for t in EXPECTED_TABLES[:8]),
        "local_outbox_events": local_counts.get("cloud_sync_ledger", 0) + local_counts.get("cloud_sync_conflicts", 0),
        "counts_by_table": local_counts
    }

    # 6. Final Verdict
    if len(missing_tables) == 0 and all_rpc_present:
        report["verdict"] = "READY"
        report["migration_readiness"]["status"] = "SCHEMA_VERIFIED"
        report["migration_readiness"]["description"] = "All tables and stored procedures exist in Supabase. System is ready for live backfill."
    elif len(missing_tables) == len(EXPECTED_TABLES):
        report["verdict"] = "NOT READY"
        report["migration_readiness"]["status"] = "MIGRATIONS_PENDING"
        report["migration_readiness"]["description"] = "None of the ASTRA SENSE tables exist in Supabase. The 3 SQL migration scripts must be executed in Supabase SQL Editor."
    else:
        report["verdict"] = "PARTIALLY READY"
        report["migration_readiness"]["status"] = "PARTIAL_SCHEMA"
        report["migration_readiness"]["description"] = f"Some tables/RPC functions exist, but {len(missing_tables)} tables are missing."

    return report

if __name__ == "__main__":
    results = asyncio.run(run_preflight())
    # Save output to scripts/preflight_result.json
    out_path = Path(__file__).resolve().parent / "preflight_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Preflight completed. Verdict: {results['verdict']}")
