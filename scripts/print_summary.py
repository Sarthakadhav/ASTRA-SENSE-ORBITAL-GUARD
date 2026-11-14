import json

with open('scripts/audit_result.json') as f:
    data = json.load(f)

print(f"Database File: {data['db_file']}")
print(f"Journal Mode: {data['journal_mode']}")
print(f"Foreign Keys Enabled: {data['foreign_keys_enabled']}\n")

for name, tbl in sorted(data['tables'].items()):
    pk = [c['name'] for c in tbl['columns'] if c['pk']]
    fks = [f"{fk['from']} -> {fk['table']}.{fk['to']}" for fk in tbl['foreign_keys']]
    idxs = [i['name'] for i in tbl['indexes']]
    print(f"Table: {name}")
    print(f"  Rows: {tbl['record_count']}")
    print(f"  Primary Key: {pk}")
    print(f"  Foreign Keys: {fks}")
    print(f"  Indexes: {idxs}")
    col_summary = [f"{c['name']} ({c['type']}{' NOT NULL' if c['notnull'] else ''})" for c in tbl['columns']]
    print(f"  Columns ({len(col_summary)}): {', '.join(col_summary)}\n")

