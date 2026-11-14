import os
import sqlite3
from pathlib import Path

print("=== CHECKING ENVIRONMENT CONFIGURATION ===")
for key in ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_DB_URL', 'SUPABASE_SYNC_ENABLED']:
    val = os.environ.get(key)
    if val:
        print(f"  {key}: CONFIGURED (len={len(val)})")
    else:
        print(f"  {key}: NOT SET")

for p in ['backend/.env', '.env', 'backend/.env.example', '.env.example']:
    path = Path(p)
    print(f"  File {p}: {'EXISTS' if path.exists() else 'DOES NOT EXIST'}")

print("\n=== SQLITE DATABASE AUDIT ===")
db_path = Path("backend/orbital_guard.db")
if not db_path.exists():
    print(f"ERROR: {db_path} does not exist!")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cursor.fetchall() if not r[0].startswith("sqlite_")]
    print(f"Found {len(tables)} user tables: {tables}")
    
    total_operational = 0
    total_sync_infra = 0
    table_counts = {}
    
    print("\nTable Breakdown:")
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t};")
        cnt = cursor.fetchone()[0]
        table_counts[t] = cnt
        if t in ["cloud_sync_outbox", "cloud_sync_conflicts"]:
            total_sync_infra += cnt
            print(f"  [SYNC INFRA] {t:25s}: {cnt:4d} rows")
        else:
            total_operational += cnt
            print(f"  [OPERATIONAL] {t:24s}: {cnt:4d} rows")
            
    print(f"\nTotal Operational Rows (8 core tables): {total_operational}")
    print(f"Total Sync Infrastructure Rows: {total_sync_infra}")
    print(f"Grand Total All Tables: {total_operational + total_sync_infra}")
    conn.close()

