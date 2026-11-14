"""
ASTRA SENSE – ORBITAL GUARD
Phase 3 Automated Test Suite: Resilience, Observability & Security Hardening
"""

import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.connection import get_db, checkpoint_wal
from app.services.sync_service import sync_service, enqueue_sync_event
from app.intelligence.telemetry_simulator import telemetry_reliability_tracker, TelemetryPacket, SensorStreamData
from app.core.auth import (
    create_session_token, validate_session, revoke_session,
    clean_expired_sessions, sanitize_text, auth_rate_limiter
)

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_module_1_sync_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/sync/metrics")
        assert res.status_code == 200
        data = res.json()
        assert "total_outbox_events" in data
        assert "system_health_score" in data
        assert "outbox_backlog_pct" in data
        assert data["system_health_score"] >= 0.0

@pytest.mark.anyio
async def test_module_3_telemetry_reliability_tracking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Check initial stream health
        res = await ac.get("/api/v1/telemetry/stream-health")
        assert res.status_code == 200
        health = res.json()
        assert "total_packets_received" in health
        assert "stream_quality_score" in health

        # Ingest a packet
        packet_payload = {
            "packet_id": 142999,
            "timestamp_met": "142:04:50:00",
            "astronaut_id": "AST-02",
            "sensor_stream": {
                "ecg_lead2_mv": 0.015,
                "heart_rate_bpm": 66.0,
                "spo2_pct": 99.1,
                "skin_temp_c": 36.6,
                "hrv_ms": 60.0,
                "sleep_debt_h": 0.5,
                "latency_drift_ms": 0.0
            },
            "battery_level_pct": 95.0,
            "crc32_valid": True,
            "is_simulated": True
        }
        res_ingest = await ac.post("/api/v1/telemetry/ingest", json=packet_payload)
        assert res_ingest.status_code == 200
        assert res_ingest.json()["status"] == "ACCEPTED"

        # Ingest duplicate packet
        res_dup = await ac.post("/api/v1/telemetry/ingest", json=packet_payload)
        assert res_dup.status_code == 200

@pytest.mark.anyio
async def test_module_4_session_lifecycle_and_sanitization():
    # 1. Create and validate token
    token = create_session_token("tester", "tester", lifetime_seconds=2)
    session = validate_session(token)
    assert session is not None
    assert session["role"] == "tester"

    # 2. Revoke token
    revoked = revoke_session(token)
    assert revoked is True
    assert validate_session(token) is None

    # 3. Input sanitization
    clean = sanitize_text("<script>alert('pwned')</script>Hello")
    assert "<script>" not in clean
    assert "&lt;script&gt;" in clean

@pytest.mark.anyio
async def test_module_7_database_wal_checkpoint():
    cp = checkpoint_wal("PASSIVE")
    assert "mode" in cp
    assert cp["busy"] in (0, 1)
    assert cp["checkpointed"] >= 0
