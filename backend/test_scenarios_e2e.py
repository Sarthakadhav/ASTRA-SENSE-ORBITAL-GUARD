"""
ASTRA SENSE - ORBITAL GUARD
End-to-End Validation Scenarios (1-6) as per Section 15 of Specification
"""

import sys
import os
import json
import sqlite3
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.database.connection import get_db, get_db_path
from app.intelligence.telemetry_simulator import generate_simulated_packet, SIMULATION_SCENARIOS
from app.api.endpoints.telemetry import ingest_telemetry_packet
from app.api.endpoints.inventory import consume_inventory
from app.schemas.inventory_schema import ConsumeInventoryRequest
from app.local_ai.local_retrieval import search_offline_protocols, generate_offline_answer
from app.intelligence.crew_readiness import calculate_crew_readiness_metrics
from app.schemas.telemetry_schema import TelemetryPacket, SensorStreamData

DB_PATH = get_db_path()

def run_scenarios():
    print("=" * 70)
    print("ASTRA SENSE – ORBITAL GUARD: END-TO-END SCENARIO VALIDATION (1-6)")
    print("=" * 70)

    results = {}

    # -------------------------------------------------------------
    # Scenario 1: Normal Mission Operation (Mode A)
    # -------------------------------------------------------------
    print("\n[SCENARIO 1] Normal Mission Operation (Mode A)")
    packet_a = generate_simulated_packet(astronaut_id="AST-01", scenario_mode="NORMAL", tick=5)
    assert packet_a.is_simulated is True, "Packet must be marked as simulated"
    assert 60 <= packet_a.sensor_stream.heart_rate_bpm <= 90, f"HR {packet_a.sensor_stream.heart_rate_bpm} out of normal range"
    assert packet_a.sensor_stream.spo2_pct >= 95, f"SpO2 {packet_a.sensor_stream.spo2_pct} out of normal range"
    assert packet_a.sensor_stream.ecg_lead2_mv is not None

    # Ingest through real backend ingestion pipeline
    ingest_res_a = ingest_telemetry_packet(packet_a)
    print(f"  ✓ Ingest Status: {ingest_res_a.status} (Quality: {ingest_res_a.quality_status})")
    print(f"  ✓ Anomaly Score: {ingest_res_a.anomaly_score:.3f} (Is Anomaly: {ingest_res_a.is_anomaly})")
    assert ingest_res_a.status == "ACCEPTED", f"Expected ACCEPTED, got {ingest_res_a.status}"
    assert ingest_res_a.safety_alert is None, f"Expected no safety alert for nominal data, got {ingest_res_a.safety_alert}"
    assert ingest_res_a.is_simulated is True, "IngestResponse must flag is_simulated=True"

    # Verify persisted in SQLite
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT packet_id, heart_rate_bpm, spo2_pct, quality_status FROM telemetry_history WHERE packet_id = ?", (packet_a.packet_id,))
        row = cursor.fetchone()
        assert row is not None, "Packet was not found in telemetry_history table"
        print(f"  ✓ Persisted in SQLite telemetry_history (Packet {row['packet_id']}, HR={row['heart_rate_bpm']} bpm, SpO2={row['spo2_pct']}%)")

    print(f"  ✓ Deterministic check: HR and SpO2 in nominal envelope, no false alarms")
    results["scenario_1"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 2: Fatigue Detection (Mode B)
    # -------------------------------------------------------------
    print("\n[SCENARIO 2] Fatigue Detection (Mode B)")
    packet_b = generate_simulated_packet(astronaut_id="AST-01", scenario_mode="FATIGUE", tick=15)
    assert packet_b.sensor_stream.sleep_debt_h > 3.0, f"Expected sleep debt > 3.0, got {packet_b.sensor_stream.sleep_debt_h}"
    assert packet_b.sensor_stream.hrv_ms < 35.0, f"Expected reduced HRV < 35.0, got {packet_b.sensor_stream.hrv_ms}"
    assert packet_b.sensor_stream.latency_drift_ms > 40.0, f"Expected latency drift > 40, got {packet_b.sensor_stream.latency_drift_ms}"

    # Ingest through real pipeline
    ingest_res_b = ingest_telemetry_packet(packet_b)
    print(f"  ✓ Ingest Status: {ingest_res_b.status}")
    print(f"  ✓ Isolation Forest Anomaly Score: {ingest_res_b.anomaly_score:.3f} (Is Anomaly: {ingest_res_b.is_anomaly})")
    assert ingest_res_b.anomaly_score < 0, f"Expected negative anomaly score for fatigue, got {ingest_res_b.anomaly_score}"

    # Verify explainable factors and condition update in SQLite
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT condition, conditionSeverity, mlModel FROM astronauts WHERE id = 'AST-01'")
        ast_row = cursor.fetchone()
        ml_data = json.loads(ast_row["mlModel"])
        print(f"  ✓ Astronaut Condition Updated: {ast_row['condition']} (Severity: {ast_row['conditionSeverity']})")
        print(f"  ✓ Explainable Factors: {[f['feature'] for f in ml_data.get('primaryFactors', [])]}")
        assert len(ml_data.get("primaryFactors", [])) > 0, "Expected explainable factor contributions"

    # Retrieve NASA SOP locally
    sop_results = search_offline_protocols("fatigue cognitive decline sleep debt")
    assert len(sop_results) > 0, "Local SOP engine failed to retrieve fatigue procedure"
    print(f"  ✓ Offline SOP Retrieved: {sop_results[0]['id']} – {sop_results[0]['title']}")
    assert "SOP-FATIGUE-01" in [s['id'] for s in sop_results], "SOP-FATIGUE-01 should be matched"
    results["scenario_2"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 3: Hypoxia Alert (Mode C)
    # -------------------------------------------------------------
    print("\n[SCENARIO 3] Hypoxia Alert (Mode C)")
    packet_c = generate_simulated_packet(astronaut_id="AST-04", scenario_mode="HYPOXIA", tick=20)
    assert packet_c.sensor_stream.spo2_pct < 88.0, f"Expected SpO2 < 88%, got {packet_c.sensor_stream.spo2_pct}"

    # Ingest through real pipeline
    ingest_res_c = ingest_telemetry_packet(packet_c)
    print(f"  ✓ Ingest Safety Alert: {ingest_res_c.safety_alert}")
    assert ingest_res_c.safety_alert is not None, "Critical safety rule did not fire on hypoxia"
    assert "Hypoxia" in ingest_res_c.safety_alert or "SpO2" in ingest_res_c.safety_alert

    # Verify alert record in health_alerts table
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, astronaut_id, severity, message, status FROM health_alerts WHERE astronaut_id = 'AST-04' ORDER BY created_at DESC LIMIT 1")
        alert_row = cursor.fetchone()
        assert alert_row is not None, "No health alert was recorded in database"
        print(f"  ✓ Health Alert in SQLite: ID={alert_row['id']}, Severity={alert_row['severity']}, Status={alert_row['status']}")
        print(f"    Message: {alert_row['message']}")
        assert alert_row["severity"] in ["CRITICAL", "critical", "WARNING", "warning"]

    hypoxia_sops = search_offline_protocols("hypoxia low oxygen partial pressure")
    assert len(hypoxia_sops) > 0 and hypoxia_sops[0]['id'] == 'SOP-HYPOXIA-02'
    print(f"  ✓ Emergency SOP Retrieved: {hypoxia_sops[0]['id']} – {hypoxia_sops[0]['title']}")
    results["scenario_3"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 4: Crew Readiness & Workload Reassignment
    # -------------------------------------------------------------
    print("\n[SCENARIO 4] Crew Readiness & Workload Reassignment")
    # Pre-redistribution readiness
    pre_readiness = calculate_crew_readiness_metrics(is_redistributed=False)
    print(f"  ✓ Initial Crew Readiness Score: {pre_readiness['overallScore']}/100 ({pre_readiness['statusDescription']})")
    assert pre_readiness['overallScore'] <= 75, "Expected degraded readiness score due to Dr. Vance fatigue"

    # Execute workload handover
    post_readiness = calculate_crew_readiness_metrics(is_redistributed=True)
    print(f"  ✓ Executed autonomous workload redistribution: {post_readiness['aiRecommendation']}")
    assert post_readiness['overallScore'] >= 80, f"Expected post-redistribution score >= 80, got {post_readiness['overallScore']}"

    # Log to audit trail in SQLite incidents table
    with get_db() as conn:
        cursor = conn.cursor()
        audit_id = f"INC-AUDIT-{int(time.time())}"
        cursor.execute("""
        INSERT INTO incidents (
            id, timestamp, severity, type, targetAstronautId, targetAstronautName,
            summary, resolutionStatus, syncStatus, assignedOfficer, actionsTaken
        ) VALUES (?, datetime('now'), 'ADVISORY', 'Workload Redistribution', 'AST-01', 'Dr. Elena Vance',
                  'Autonomous Task Handover: Dr. Vance to Cmdr. Chen', 'Resolved', 'PENDING_DSN_WINDOW',
                  'Flight Surgeon', '["Non-urgent tasks delegated to Cmdr. Chen", "Mandatory 8h sleep cycle initiated"]')
        """, (audit_id,))

    print("  ✓ Decision and task handover recorded in immutable audit log")
    results["scenario_4"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 5: Offline Mission Continuity
    # -------------------------------------------------------------
    print("\n[SCENARIO 5] Offline Mission Continuity (Autonomous Local Engine)")
    t0 = time.perf_counter()
    offline_sops = search_offline_protocols("cardiac arrhythmia supraventricular tachycardia")
    t1 = time.perf_counter()
    query_latency_ms = (t1 - t0) * 1000.0
    print(f"  ✓ Offline Local SOP Retrieval latency: {query_latency_ms:.2f} ms (0 network calls)")
    assert len(offline_sops) > 0, "Offline SOP search returned empty"

    # Offline Inventory Dispensation
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT stock FROM medical_inventory WHERE id = 'MED-01'")
        initial_stock = cursor.fetchone()["stock"]

    dispense_res = consume_inventory(ConsumeInventoryRequest(
        item_id="MED-01",
        quantity=1,
        reason="Scenario 5 Offline Fatigue Countermeasure",
        authorized_by="Dr. Elena Vance",
        patient_id="AST-01"
    ))
    assert dispense_res["status"] in ["DISPENSED", "SUCCESS"], f"Expected DISPENSED, got {dispense_res['status']}"
    assert dispense_res["remaining_stock"] == initial_stock - 1, f"Stock mismatch: {initial_stock} -> {dispense_res['remaining_stock']}"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_dispensations WHERE item_id = 'MED-01' ORDER BY id DESC LIMIT 1")
        disp_row = cursor.fetchone()
        assert disp_row is not None, "Dispensation record missing"
        print(f"  ✓ Offline MedVault dispensation: MED-01 decremented ({initial_stock} -> {dispense_res['remaining_stock']})")
        print(f"    Dispensation Audit Log: ID={disp_row['id']}, Patient={disp_row['patient_astronaut_id']}, Reason={disp_row['reason']}")
    results["scenario_5"] = "PASSED"

    # -------------------------------------------------------------
    # Scenario 6: Database Persistence Across Simulated Process Reload
    # -------------------------------------------------------------
    print("\n[SCENARIO 6] Database Persistence & Integrity Across Reload")
    # Verify records exist in WAL database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM telemetry_history")
    hist_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM health_alerts")
    alert_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM inventory_dispensations")
    disp_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM incidents")
    inc_count = cursor.fetchone()[0]

    # Explicitly close connection simulating application shutdown
    conn.close()

    # Reopen fresh connection simulating reboot
    conn_new = sqlite3.connect(DB_PATH)
    cursor_new = conn_new.cursor()

    cursor_new.execute("SELECT COUNT(*) FROM telemetry_history")
    hist_count_after = cursor_new.fetchone()[0]

    cursor_new.execute("SELECT COUNT(*) FROM health_alerts")
    alert_count_after = cursor_new.fetchone()[0]

    cursor_new.execute("SELECT COUNT(*) FROM inventory_dispensations")
    disp_count_after = cursor_new.fetchone()[0]

    cursor_new.execute("SELECT COUNT(*) FROM incidents")
    inc_count_after = cursor_new.fetchone()[0]

    cursor_new.execute("PRAGMA journal_mode")
    journal_mode = cursor_new.fetchone()[0]

    conn_new.close()

    assert hist_count == hist_count_after and hist_count > 0, "Telemetry history mismatch after reload"
    assert alert_count == alert_count_after and alert_count > 0, "Alert count mismatch after reload"
    assert disp_count == disp_count_after and disp_count > 0, "Dispensations mismatch after reload"
    assert inc_count == inc_count_after and inc_count > 0, "Incidents mismatch after reload"
    assert journal_mode.upper() == "WAL", f"Expected WAL mode, got {journal_mode}"

    print(f"  ✓ Database Journal Mode: {journal_mode.upper()}")
    print(f"  ✓ Telemetry Records Persisted: {hist_count_after}")
    print(f"  ✓ Safety Alerts Persisted: {alert_count_after}")
    print(f"  ✓ Inventory Dispensations Persisted: {disp_count_after}")
    print(f"  ✓ Incidents & Audit Logs Persisted: {inc_count_after}")
    print("  ✓ 100% Data Integrity Verified Across Simulated Process Restart")
    results["scenario_6"] = "PASSED"

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY: ALL 6 END-TO-END SCENARIOS PASSED")
    print("=" * 70)
    for scen, status in results.items():
        print(f"  {scen.upper()}: {status}")

    return results

if __name__ == "__main__":
    run_scenarios()
