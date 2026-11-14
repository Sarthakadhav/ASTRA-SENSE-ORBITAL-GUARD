"""
ASTRA SENSE – ORBITAL GUARD
Phase 2: Supabase Hybrid Synchronization Test Suite
Validates transactional outbox, dependency ordering, sync status,
idempotency, conflict resolution, and offline resilience.
"""

import json
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from app.main import app
from app.database.connection import get_db
from app.services.sync_service import (
    enqueue_sync_event,
    CloudSyncService,
    ENTITY_DEPENDENCY_ORDER
)
from app.database.supabase_client import supabase_manager


@pytest.mark.anyio
async def test_sync_status_endpoint():
    """Verify GET /api/v1/sync/status returns comprehensive sync metrics."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/sync/status")
        assert res.status_code == 200
        data = res.json()
        assert "pipeline_state" in data
        assert "cloud_configured" in data
        assert "cloud_connected" in data
        assert "pending_count" in data
        assert "synced_count" in data
        assert "failed_count" in data
        assert "unresolved_conflicts" in data
        assert data["pipeline_state"] in ("LOCAL_ONLY", "CLOUD_CONNECTED", "OFFLINE", "OFFLINE_QUEUED", "SYNCING", "SYNC_PENDING", "CONFLICT_DETECTED")


@pytest.mark.anyio
async def test_outbox_transactional_atomicity():
    """Verify that enqueuing an outbox event is bound to SQLite transaction boundaries."""
    # 1. Successful commit
    test_record_id = "TEST-REC-001"
    with get_db() as conn:
        cursor = conn.cursor()
        evt_id = enqueue_sync_event(
            cursor=cursor,
            entity_type="incidents",
            record_id=test_record_id,
            operation="INSERT",
            payload={"id": test_record_id, "summary": "Outbox atomicity verification"}
        )
        conn.commit()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cloud_sync_outbox WHERE id = ?;", (evt_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["record_id"] == test_record_id
        assert row["status"] == "PENDING"

    # 2. Rollback test
    rollback_id = "TEST-REC-ROLLBACK"
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            enqueue_sync_event(
                cursor=cursor,
                entity_type="incidents",
                record_id=rollback_id,
                operation="INSERT",
                payload={"id": rollback_id}
            )
            # Force intentional exception before commit
            raise ValueError("Intentional rollback test")
    except ValueError:
        pass

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cloud_sync_outbox WHERE record_id = ?;", (rollback_id,))
        assert cursor.fetchone() is None


@pytest.mark.anyio
async def test_get_outbox_events_endpoint():
    """Verify GET /api/v1/sync/outbox returns queued events."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/sync/outbox?limit=5")
        assert res.status_code == 200
        events = res.json()
        assert isinstance(events, list)
        if events:
            assert "entity_type" in events[0]
            assert "operation" in events[0]
            assert "status" in events[0]


@pytest.mark.anyio
async def test_conflict_recording_and_resolution():
    """Verify recording and resolving sync conflicts via /api/v1/sync/conflicts/resolve."""
    conflict_id = "CONF-TEST-99"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO cloud_sync_conflicts (
            id, entity_type, record_id, local_payload_json, cloud_payload_json,
            conflict_reason, resolution_status
        ) VALUES (?, ?, ?, ?, ?, ?, 'UNRESOLVED');
        """, (
            conflict_id,
            "medical_inventory",
            "MED-01",
            json.dumps({"stock": 70}),
            json.dumps({"stock": 72}),
            "Version divergence during offline partition"
        ))
        conn.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Check conflict appears in list
        get_res = await client.get("/api/v1/sync/conflicts")
        assert get_res.status_code == 200
        conflicts = get_res.json()
        target = next((c for c in conflicts if c["id"] == conflict_id), None)
        assert target is not None
        assert target["resolution_status"] == "UNRESOLVED"

        # Resolve conflict with RESOLVED_LOCAL
        resolve_payload = {
            "conflict_id": conflict_id,
            "resolution_choice": "RESOLVED_LOCAL",
            "resolved_by": "Cmdr. Sarah Chen"
        }
        res = await client.post("/api/v1/sync/conflicts/resolve", json=resolve_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["resolution"] == "RESOLVED_LOCAL"

    # Confirm in DB
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT resolution_status, resolved_by FROM cloud_sync_conflicts WHERE id = ?;", (conflict_id,))
        row = cursor.fetchone()
        assert row["resolution_status"] == "RESOLVED_LOCAL"
        assert row["resolved_by"] == "Cmdr. Sarah Chen"


@pytest.mark.anyio
async def test_sync_retry_reset_endpoint():
    """Verify POST /api/v1/sync/retry resets retry counters and failed status."""
    evt_fail_id = "EVT-FAIL-RESET-01"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO cloud_sync_outbox (
            id, entity_type, record_id, operation, payload_json, status, attempt_count, error_info
        ) VALUES (?, 'telemetry_history', '142099', 'INSERT', '{}', 'FAILED', 5, 'Network timeout');
        """, (evt_fail_id,))
        conn.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/sync/retry")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["reset_count"] >= 1

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, attempt_count, error_info FROM cloud_sync_outbox WHERE id = ?;", (evt_fail_id,))
        row = cursor.fetchone()
        assert row["status"] == "PENDING"
        assert row["attempt_count"] == 0
        assert row["error_info"] is None


def test_entity_dependency_ordering():
    """Verify that foreign-key parent tables precede dependent tables in sync order."""
    assert ENTITY_DEPENDENCY_ORDER.index("astronauts") < ENTITY_DEPENDENCY_ORDER.index("telemetry_history")
    assert ENTITY_DEPENDENCY_ORDER.index("astronauts") < ENTITY_DEPENDENCY_ORDER.index("health_alerts")
    assert ENTITY_DEPENDENCY_ORDER.index("medical_inventory") < ENTITY_DEPENDENCY_ORDER.index("inventory_dispensations")


@pytest.mark.anyio
async def test_mock_cloud_sync_execution():
    """Verify batch synchronization with mocked Supabase PostgREST client."""
    test_evt_id = "EVT-MOCK-SYNC-01"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO cloud_sync_outbox (
            id, entity_type, record_id, operation, payload_json, status, attempt_count, created_at
        ) VALUES (?, 'astronauts', 'AST-01', 'UPDATE', '{\"id\": \"AST-01\", \"condition\": \"Healthy\"}', 'PENDING', 0, '1970-01-01 00:00:00');
        """, (test_evt_id,))
        conn.commit()

    service = CloudSyncService()

    # Mock test_connection and upsert_record to simulate active cloud reachability
    with patch.object(supabase_manager, "test_connection", new_callable=AsyncMock) as mock_conn, \
         patch.object(supabase_manager, "upsert_record", new_callable=AsyncMock) as mock_upsert, \
         patch.object(supabase_manager, "_test_mode_override", True):

        mock_conn.return_value = {"connected": True, "configured": True, "status": "ONLINE"}
        mock_upsert.return_value = {"status": "SUCCESS"}

        res = await service.process_sync_batch(limit=10)
        assert res["status"] in ("COMPLETED", "SUCCESS", "PARTIAL")
        assert res["synced"] >= 1

    # Verify that the outbox record transitioned to SYNCED
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM cloud_sync_outbox WHERE id = ?;", (test_evt_id,))
        row = cursor.fetchone()
        assert row["status"] == "SYNCED"


@pytest.mark.anyio
async def test_sync_trigger_endpoint_offline():
    """Verify POST /api/v1/sync/trigger handles offline cloud gracefully."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/sync/trigger")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "processed" in data
        assert "synced" in data
        assert "failed" in data
