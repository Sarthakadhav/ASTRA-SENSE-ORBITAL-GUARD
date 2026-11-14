import sqlite3
import os
import time

def optimize_local_db():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "orbital_guard.db"))
    print(f"=== OPTIMIZING SQLITE DATABASE: {db_path} ===")
    
    t0 = time.perf_counter()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Composite indexes
        print("Creating high-performance composite indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_ast_time ON telemetry_history (astronaut_id, timestamp_met);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status_retry ON cloud_sync_outbox (status, next_retry_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status_sev ON health_alerts (status, severity);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dispensations_time ON inventory_dispensations (timestamp_met);")
        
        # 2. PRAGMA optimize
        print("Running PRAGMA optimize...")
        cursor.execute("PRAGMA optimize;")
        
        # 3. WAL Checkpoint TRUNCATE
        print("Executing WAL Checkpoint TRUNCATE...")
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        cp_res = cursor.fetchone()
        print(f"WAL Checkpoint Result: busy={cp_res[0]}, log_frames={cp_res[1]}, checkpointed={cp_res[2]}")
        
        conn.commit()

    duration_ms = (time.perf_counter() - t0) * 1000
    print(f"Optimization completed in {duration_ms:.2f} ms.")

if __name__ == "__main__":
    optimize_local_db()

