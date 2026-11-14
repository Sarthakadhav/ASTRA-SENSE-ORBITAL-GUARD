import sqlite3

conn = sqlite3.connect('backend/orbital_guard.db')
cursor = conn.cursor()
cursor.execute("SELECT id, entity_type, record_id, status, payload_json FROM cloud_sync_outbox WHERE status IN ('PENDING', 'RETRY') LIMIT 10;")
for r in cursor.fetchall():
    print(r[0], r[1], r[2], r[3], r[4][:90])
