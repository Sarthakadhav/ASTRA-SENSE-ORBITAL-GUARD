import pytest
import httpx
from app.main import app
from app.api.endpoints.crew import reset_crew_simulation

@pytest.fixture(autouse=True)
def setup_baseline():
    reset_crew_simulation()

@pytest.mark.anyio
async def test_root_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "FLIGHT_ACTIVE"
        assert "/docs" in data["api_documentation"]

@pytest.mark.anyio
async def test_get_crew():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/crew")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 4
        vance = next(a for a in data if a["id"] == "AST-01")
        assert vance["name"] == "Dr. Elena Vance"

@pytest.mark.anyio
async def test_crew_readiness():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/crew/readiness")
        assert res.status_code == 200
        data = res.json()
        assert data["overallScore"] == 68
        assert len(data["dimensions"]) == 4

@pytest.mark.anyio
async def test_workload_redistribution():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "primary_astronaut_id": "AST-01",
            "backup_astronaut_id": "AST-02",
            "approved_by": "Cmdr. Sarah Chen",
            "reason": "Elevated neuro-fatigue and cognitive latency drift"
        }
        res = await client.post("/api/v1/crew/redistribute", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "EXECUTED"
        assert data["new_crew_readiness_score"] == 82
        assert data["primary_astronaut"]["condition"] == "Resting / Relieved"

@pytest.mark.anyio
async def test_isolation_forest_scoring():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "astronaut_id": "AST-01",
            "heart_rate": 84.0,
            "heart_rate_baseline": 64.0,
            "hrv": 24.0,
            "spo2": 96.0,
            "temperature": 37.1,
            "temperature_baseline": 36.6,
            "sleep_debt_hours": 6.4,
            "cognitive_latency_delta_ms": 185.0
        }
        res = await client.post("/api/v1/ml/isolation-forest", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "anomalyScore" in data
        assert data["anomalyScore"] < 0
        assert data["is_anomaly"] is True

@pytest.mark.anyio
async def test_telemetry_ingest():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        sample_packet = {
            "packet_id": 142099,
            "timestamp_met": "142:04:36:20",
            "astronaut_id": "AST-01",
            "sensor_stream": {
                "ecg_lead2_mv": 1.14,
                "spo2_pct": 96.0,
                "heart_rate_bpm": 84.0,
                "skin_temp_c": 37.1,
                "imu_accel_g": [0.02, 0.04, 0.01],
                "impedance_ohms": 480.0
            },
            "battery_level_pct": 94.0,
            "crc32_valid": True
        }
        res = await client.post("/api/v1/telemetry/ingest", json=sample_packet)
        assert res.status_code == 200
        data = res.json()
        assert data["quality_status"] == "OPTIMAL"
        assert data["packet_id"] == 142099

@pytest.mark.anyio
async def test_offline_ai_assistant():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "question": "What is the clinical protocol for astronaut acute fatigue and high sleep debt?",
            "astronaut_id": "AST-01",
            "include_vitals": True
        }
        res = await client.post("/api/v1/assistant/ask", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert len(data["answer"]) > 20
        assert data["intelligence_mode"] in ("ONLINE_GEMINI_AI", "OFFLINE_FLIGHT_KNOWLEDGE")

@pytest.mark.anyio
async def test_medical_inventory():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/inventory")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 8

@pytest.mark.anyio
async def test_inventory_consume():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "item_id": "MED-01",
            "quantity": 1,
            "reason": "Emergency fatigue countermeasure",
            "authorized_by": "Dr. Elena Vance"
        }
        res = await client.post("/api/v1/inventory/consume", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DISPENSED"

@pytest.mark.anyio
async def test_dsn_sync_queue():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/dsn/sync-queue")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DSN_TRANSMISSION_COMPLETE"

@pytest.mark.anyio
async def test_system_status():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/system/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "OPERATIONAL"
        assert data["offline_capabilities"]["is_earth_independent"] is True

@pytest.mark.anyio
async def test_simulation_scenarios_and_step():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Get scenarios
        scen_res = await client.get("/api/v1/telemetry/simulator/scenarios")
        assert scen_res.status_code == 200
        scenarios = scen_res.json()
        assert len(scenarios) >= 5

        # Execute simulation step for Mode A
        step_res = await client.post("/api/v1/telemetry/simulator/step", json={
            "astronaut_id": "AST-02",
            "scenario_mode": "NORMAL",
            "tick": 2
        })
        assert step_res.status_code == 200
        s_data = step_res.json()
        assert s_data["data_label"] == "SIMULATED TELEMETRY"
        assert s_data["ingest_result"]["status"] == "ACCEPTED"

        # Execute simulation step for Mode C (Hypoxia)
        hypo_res = await client.post("/api/v1/telemetry/simulator/step", json={
            "astronaut_id": "AST-01",
            "scenario_mode": "HYPOXIA",
            "tick": 20
        })
        assert hypo_res.status_code == 200
        h_data = hypo_res.json()
        assert h_data["packet"]["sensor_stream"]["spo2_pct"] < 90.0

@pytest.mark.anyio
async def test_inventory_replenish_and_dispensations():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        rep_res = await client.post("/api/v1/inventory/replenish", json={
            "item_id": "MED-01",
            "quantity": 5,
            "authorized_by": "Cmdr. Sarah Chen",
            "notes": "Testing cargo restock"
        })
        assert rep_res.status_code == 200
        assert rep_res.json()["added_quantity"] == 5

        disp_res = await client.get("/api/v1/inventory/dispensations")
        assert disp_res.status_code == 200
        assert isinstance(disp_res.json(), list)

@pytest.mark.anyio
async def test_incident_create_and_resolve():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        inc_res = await client.post("/api/v1/incidents", json={
            "severity": "WARNING",
            "type": "Treadmill Vibration Resonance",
            "targetAstronautId": "AST-02",
            "targetAstronautName": "Cmdr. Sarah Chen",
            "summary": "T2 treadmill vibration isolator showed minor resonance harmonic.",
            "assignedOfficer": "Lt. Marcus Reyes",
            "actionsTaken": ["Recalibrated magnetic dampers"]
        })
        assert inc_res.status_code == 200
        inc_id = inc_res.json()["incident_id"]

        resolve_res = await client.patch(f"/api/v1/incidents/{inc_id}/resolve", json={
            "resolution_notes": "Harmonic dampening test passed within NASA-STD-3001 margins.",
            "resolved_by": "Lt. Marcus Reyes"
        })
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == "RESOLVED"

@pytest.mark.anyio
async def test_dsn_queue_status():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/dsn/queue")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "QUEUE_READY"
        assert "pending_incidents_count" in data

@pytest.mark.anyio
async def test_role_auth_student_and_faculty():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Student login
        res_stud = await client.post("/api/v1/auth/login", json={
            "username": "student",
            "password": "Student2026!"
        })
        assert res_stud.status_code == 200
        s_data = res_stud.json()
        assert s_data["role"] == "student"
        assert s_data["permissions"]["can_redistribute_workload"] is False

        # Faculty login
        res_fac = await client.post("/api/v1/auth/login", json={
            "username": "faculty",
            "password": "Faculty2026!"
        })
        assert res_fac.status_code == 200
        f_data = res_fac.json()
        assert f_data["role"] == "faculty"
        assert f_data["permissions"]["can_redistribute_workload"] is True
