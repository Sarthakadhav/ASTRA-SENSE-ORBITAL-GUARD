import sys
import time
from pathlib import Path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.database.init_db import init_database
from app.api.endpoints.crew import get_crew, get_crew_readiness, redistribute_workload, reset_crew_simulation
from app.schemas.crew_schema import WorkloadRedistributionRequest
from app.api.endpoints.telemetry import (
    get_simulation_scenarios, step_simulation, get_telemetry_history, get_latest_telemetry
)
from app.schemas.telemetry_schema import SimulatorStepRequest
from app.api.endpoints.inventory import (
    get_inventory, consume_inventory, replenish_inventory, create_inventory_item, get_dispensations
)
from app.schemas.inventory_schema import (
    ConsumeInventoryRequest, ReplenishInventoryRequest, CreateInventoryItemRequest
)
from app.api.endpoints.incidents import get_incidents, create_incident, resolve_incident
from app.schemas.incident_schema import IncidentCreate, IncidentResolveRequest
from app.api.endpoints.dsn import get_dsn_queue, sync_dsn_queue
from app.api.endpoints.assistant import ask_ai_assistant
from app.schemas.assistant_schema import AssistantQueryRequest
from app.api.endpoints.alerts import get_alerts, acknowledge_alert, resolve_alert
from app.schemas.alert_schema import AlertAcknowledgeRequest, AlertResolveRequest
from app.api.endpoints.auth import login, get_current_user
from app.api.endpoints.auth import LoginRequest

def run_tests():
    print(">>> 1. Initializing DB & Resetting baseline")
    init_database()
    reset_crew_simulation()

    print(">>> 2. Testing Telemetry Simulator Scenarios")
    scenarios = get_simulation_scenarios()
    assert len(scenarios) >= 5, f"Expected at least 5 scenarios, got {len(scenarios)}"
    scenario_ids = [s["id"] for s in scenarios]
    assert "NORMAL" in scenario_ids
    assert "FATIGUE" in scenario_ids
    assert "HYPOXIA" in scenario_ids
    assert "CARDIAC" in scenario_ids
    assert "CUSTOM" in scenario_ids
    print(f"Verified scenarios: {scenario_ids}")

    print(">>> 3. Testing Simulator Step Ingestion Pipeline")
    # Mode A: Normal
    step_res_a = step_simulation(SimulatorStepRequest(astronaut_id="AST-02", scenario_mode="NORMAL", tick=1))
    assert step_res_a.data_label == "SIMULATED TELEMETRY"
    assert step_res_a.ingest_result.status == "ACCEPTED"
    print(f"Mode A (Normal) accepted: packet #{step_res_a.packet.packet_id}, HR={step_res_a.packet.sensor_stream.heart_rate_bpm}")

    # Mode B: Fatigue
    step_res_b = step_simulation(SimulatorStepRequest(astronaut_id="AST-01", scenario_mode="FATIGUE", tick=5))
    assert step_res_b.ingest_result.is_anomaly is True
    print(f"Mode B (Fatigue) anomaly score: {step_res_b.ingest_result.anomaly_score}")

    # Mode C: Hypoxia
    step_res_c = step_simulation(SimulatorStepRequest(astronaut_id="AST-03", scenario_mode="HYPOXIA", tick=20))
    print(f"Mode C (Hypoxia) SpO2: {step_res_c.packet.sensor_stream.spo2_pct}%, Alert: {step_res_c.ingest_result.safety_alert}")
    assert step_res_c.packet.sensor_stream.spo2_pct < 90.0
    assert step_res_c.ingest_result.safety_alert is not None

    # Mode D: Cardiac Irregularity
    step_res_d = step_simulation(SimulatorStepRequest(astronaut_id="AST-04", scenario_mode="CARDIAC", tick=10))
    print(f"Mode D (Cardiac) HR: {step_res_d.packet.sensor_stream.heart_rate_bpm} bpm, Alert: {step_res_d.ingest_result.safety_alert}")
    assert step_res_d.packet.sensor_stream.heart_rate_bpm > 125.0

    # Mode E: Custom
    step_res_e = step_simulation(SimulatorStepRequest(
        astronaut_id="AST-01",
        scenario_mode="CUSTOM",
        tick=1,
        custom_params={
            "heart_rate_bpm": 74.0,
            "spo2_pct": 98.0,
            "skin_temp_c": 36.8,
            "hrv_ms": 48.0,
            "sleep_debt_h": 1.5,
            "latency_drift_ms": 10.0,
            "impedance_ohms": 460.0
        }
    ))
    assert step_res_e.packet.sensor_stream.heart_rate_bpm == 74.0

    print(">>> 4. Testing Telemetry History & Latest")
    history = get_telemetry_history("AST-01", limit=10)
    assert len(history) > 0
    latest = get_latest_telemetry("AST-01")
    assert latest["is_simulated"] is True

    print(">>> 5. Testing Inventory Operations: Replenish, Add Item, Dispensations")
    rep_res = replenish_inventory(ReplenishInventoryRequest(item_id="MED-04", quantity=5, authorized_by="Cmdr. Sarah Chen"))
    assert rep_res["added_quantity"] == 5
    print(f"Replenished TXA: New Stock = {rep_res['new_stock']}")

    test_item_id = f"MED-T{int(time.time()) % 10000}"
    new_item_res = create_inventory_item(CreateInventoryItemRequest(
        id=test_item_id,
        category="Supplies",
        name="Emergency Burn Dressing & Hydrogel",
        indication="Thermal flash & electrical burns",
        stock=10,
        unit="dressings",
        minSafeStock=4,
        shelfLifeDays=720,
        vitalUrgency="High"
    ))
    assert new_item_res["item_id"] == test_item_id
    print(f"Created new inventory item: {new_item_res['name']}")

    consume_res = consume_inventory(ConsumeInventoryRequest(
        item_id=test_item_id,
        quantity=2,
        reason="Skin contact test burn protocol",
        authorized_by="Dr. Elena Vance",
        patient_id="AST-03"
    ))
    assert consume_res["remaining_stock"] == 8

    disp_list = get_dispensations()
    assert len(disp_list) > 0
    print(f"Dispensation records: {len(disp_list)} logged.")

    print(">>> 6. Testing Incidents: Create & Resolve")
    import asyncio
    inc_res = asyncio.run(create_incident(IncidentCreate(
        severity="WARNING",
        type="Thermal Excursion in Lab Module",
        targetAstronautId="AST-03",
        targetAstronautName="Lt. Marcus Reyes",
        summary="Transient thermal spike in rack electronics. Coolant loop restored.",
        assignedOfficer="Cmdr. Sarah Chen",
        actionsTaken=["Engaged auxiliary cooling", "Isolated rack circuit"]
    )))
    inc_id = inc_res["incident_id"]
    print(f"Created incident: {inc_id}")

    resolve_res = resolve_incident(inc_id, IncidentResolveRequest(
        resolution_notes="Coolant temperature normalized to 18.5°C. System nominal.",
        resolved_by="Cmdr. Sarah Chen"
    ))
    assert resolve_res["status"] == "RESOLVED"
    print(f"Resolved incident: {inc_id}")

    print(">>> 7. Testing DSN Earth Sync Queue")
    dsn_q = get_dsn_queue()
    print(f"DSN Queue: {dsn_q['pending_incidents_count']} items pending transmission.")

    dsn_sync = sync_dsn_queue()
    assert dsn_sync.status == "DSN_TRANSMISSION_COMPLETE"
    print(f"DSN Batch Synced: {dsn_sync.synced_events_count} events.")

    print(">>> 8. Testing Role-based Authentication")
    # Student login
    login_stud = login(LoginRequest(username="student", password="Student2026!"))
    assert login_stud.role == "student"
    assert login_stud.permissions["can_redistribute_workload"] is False

    # Faculty login
    login_fac = login(LoginRequest(username="faculty", password="Faculty2026!"))
    assert login_fac.role == "faculty"
    assert login_fac.permissions["can_redistribute_workload"] is True
    assert login_fac.permissions["can_resolve_incidents"] is True
    print("Authentication & role permissions verified.")

    print(">>> 9. Testing Alerts Lifecycle: Acknowledge & Resolve")
    alerts = get_alerts()
    if alerts:
        alt_id = alerts[0]["id"]
        ack_res = acknowledge_alert(alt_id, AlertAcknowledgeRequest(officer_id="Cmdr. Sarah Chen", notes="Reviewing vitals"))
        assert ack_res["status"] == "ACKNOWLEDGED"
        res_res = resolve_alert(alt_id, AlertResolveRequest(officer_id="Cmdr. Sarah Chen", resolution_notes="Vitals returned to baseline"))
        assert res_res["status"] == "RESOLVED"
        print(f"Alert lifecycle complete for {alt_id}")

    print("\n" + "="*60)
    print(">>> ALL EXPANDED ORBITAL GUARD SUBSYSTEM TESTS PASSED! <<<")
    print("="*60)

if __name__ == "__main__":
    run_tests()
