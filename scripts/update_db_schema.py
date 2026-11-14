with open('backend/app/database/init_db.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        # Audit Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_officer TEXT,
            action TEXT NOT NULL,
            details TEXT,
            timestamp_met TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Seed initial crew if empty'''

replacement = '''        # Audit Logs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_officer TEXT,
            action TEXT NOT NULL,
            details TEXT,
            timestamp_met TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Inventory Dispensations Ledger Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_dispensations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            patient_astronaut_id TEXT,
            reason TEXT NOT NULL,
            authorized_by TEXT NOT NULL,
            timestamp_met TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Performance Indexes for high-frequency telemetry & queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_history_ast ON telemetry_history (astronaut_id, created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_alerts_ast ON health_alerts (astronaut_id, status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents (syncStatus);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispensations_item ON inventory_dispensations (item_id);")

        # Seed initial crew if empty'''

assert target in text, "Target block not found in init_db.py"
text = text.replace(target, replacement, 1)
with open('backend/app/database/init_db.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("init_db.py updated successfully!")

