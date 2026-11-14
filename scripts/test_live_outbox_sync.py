import asyncio
import os
import sys

# Ensure backend path is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.sync_service import sync_service
from app.database.connection import get_db

async def main():
    print("=== LIVE OUTBOX SYNCHRONIZATION TEST ===")
    
    # Reset failed/retry events
    reset_res = await sync_service.retry_failed_events()
    print(f"Reset result: {reset_res}")

    # Check how many pending
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, count(*) FROM cloud_sync_outbox GROUP BY status")
        print("Outbox status before sync:", [tuple(r) for r in cursor.fetchall()])

    # Process batch in loop until 0 remaining or max iterations
    iteration = 0
    while iteration < 10:
        iteration += 1
        print(f"\n--- SYNC LOOP {iteration} ---")
        await sync_service.retry_failed_events()
        batch_res = await sync_service.process_sync_batch(limit=100)
        print(f"Batch sync result: {batch_res}")
        if batch_res.get("failed", 0) == 0 and batch_res.get("retry_scheduled", 0) == 0:
            print(">>> ALL OUTBOX EVENTS FULLY SYNCHRONIZED! <<<")
            break

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, count(*) FROM cloud_sync_outbox GROUP BY status")
        print("\nFinal Outbox status:", [tuple(r) for r in cursor.fetchall()])

if __name__ == "__main__":
    asyncio.run(main())
