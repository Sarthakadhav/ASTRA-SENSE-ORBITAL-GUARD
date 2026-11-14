from typing import List, Dict, Any
from fastapi import APIRouter
from app.database.connection import get_db
from app.schemas.incident_schema import DSNSyncResponse, DSNQueueItem
from app.config import settings

router = APIRouter()

@router.get("/dsn/queue", summary="View items pending Deep Space Network Earth transmission")
def get_dsn_queue():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, type, timestamp, summary, syncStatus
        FROM incidents
        WHERE syncStatus LIKE '%Queue%' OR syncStatus LIKE '%Cached%'
        ORDER BY created_at DESC;
        """)
        rows = cursor.fetchall()
        queued_items = [
            {
                "id": r["id"],
                "type": r["type"],
                "timestamp": r["timestamp"],
                "summary": r["summary"],
                "sync_status": r["syncStatus"]
            }
            for r in rows
        ]

        cursor.execute("SELECT COUNT(*) FROM telemetry_history WHERE is_anomaly = 1;")
        anomaly_telemetry_count = cursor.fetchone()[0]

    return {
        "status": "QUEUE_READY",
        "pending_incidents_count": len(queued_items),
        "anomaly_telemetry_count": anomaly_telemetry_count,
        "dsn_latency_seconds": settings.DSN_LATENCY_SECONDS,
        "dsn_latency_display": "14m 22s Earth-Mars Delay",
        "station": "Goldstone DSN Antenna 14",
        "items": queued_items
    }

@router.post("/dsn/sync-queue", response_model=DSNSyncResponse, summary="Batch sync cached telemetry & incidents to Earth")
def sync_dsn_queue():
    """
    Simulates batch transmission over NASA Deep Space Network with 14-minute latency window.
    Marks cached offline incidents as synced with Houston Mission Control.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE syncStatus LIKE '%Queue%' OR syncStatus LIKE '%Cached%';")
        queued_count = cursor.fetchone()[0]

        cursor.execute("""
        UPDATE incidents
        SET syncStatus = 'Synced with Houston Mission Control'
        WHERE syncStatus LIKE '%Queue%' OR syncStatus LIKE '%Cached%';
        """)
        synced_count = cursor.rowcount

        cursor.execute("""
        INSERT INTO audit_logs (user_officer, action, details, timestamp_met)
        VALUES (?, ?, ?, ?);
        """, (
            "Comms Officer",
            "DSN_BATCH_SYNC",
            f"Transmitted {synced_count} queued incident packets across Goldstone DSN uplink.",
            "MET 142d 05:15:00"
        ))

        conn.commit()

    return DSNSyncResponse(
        status="DSN_TRANSMISSION_COMPLETE",
        queued_events_count=queued_count,
        synced_events_count=synced_count,
        latency_seconds=settings.DSN_LATENCY_SECONDS,
        dsn_station="Goldstone DSN 70m Deep Space Antenna (DSS-14)",
        details=f"Successfully transmitted {synced_count} event records to Houston Mission Control across DSN uplink."
    )
