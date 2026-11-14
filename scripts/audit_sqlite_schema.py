import sqlite3
import json
from pathlib import Path

db_path = Path("backend/orbital_guard.db")
if not db_path.exists():
    print(f"Error: {db_path} does not exist!")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get journal mode and foreign keys
cursor.execute("PRAGMA journal_mode;")
journal_mode = cursor.fetchone()[0]
cursor.execute("PRAGMA foreign_keys;")
foreign_keys_enabled = bool(cursor.fetchone()[0])

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]

schema_audit = {
    "db_file": str(db_path.resolve()),
    "journal_mode": journal_mode,
    "foreign_keys_enabled": foreign_keys_enabled,
    "tables": {}
}

for table in tables:
    cursor.execute(f"PRAGMA table_info('{table}');")
    cols = cursor.fetchall()

    cursor.execute(f"PRAGMA foreign_key_list('{table}');")
    fks = cursor.fetchall()

    cursor.execute(f"PRAGMA index_list('{table}');")
    idxs = cursor.fetchall()

    cursor.execute(f"SELECT COUNT(*) FROM '{table}';")
    count = cursor.fetchone()[0]

    # Sample record
    cursor.execute(f"SELECT * FROM '{table}' LIMIT 1;")
    sample_row = cursor.fetchone()
    sample_dict = dict(sample_row) if sample_row else None

    schema_audit["tables"][table] = {
        "record_count": count,
        "columns": [
            {
                "cid": c["cid"],
                "name": c["name"],
                "type": c["type"],
                "notnull": bool(c["notnull"]),
                "default": c["dflt_value"],
                "pk": bool(c["pk"])
            }
            for c in cols
        ],
        "foreign_keys": [
            {
                "id": f["id"],
                "table": f["table"],
                "from": f["from"],
                "to": f["to"]
            }
            for f in fks
        ],
        "indexes": [
            {
                "name": i["name"],
                "unique": bool(i["unique"])
            }
            for i in idxs
        ],
        "sample_fields": list(sample_dict.keys()) if sample_dict else []
    }

print(json.dumps(schema_audit, indent=2))

with open("scripts/audit_result.json", "w") as f:
    json.dump(schema_audit, f, indent=2)

print("\nAudit written to scripts/audit_result.json")

