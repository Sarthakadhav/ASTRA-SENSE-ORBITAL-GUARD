import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from app.schemas.telemetry_schema import (
    TelemetryPacket, IngestResponse,
    SimulatorStepRequest, SimulatorStepResponse
)
from app.database.connection import get_db
from app.intelligence.decision_engine import assess_telemetry_event
from app.intelligence.telemetry_simulator import (
    SIMULATION_SCENARIOS, generate_simulated_packet, telemetry_reliability_tracker
)
from app.core.logging import logger
from app.services.sync_service import enqueue_sync_event

router = APIRouter()

@router.post("/telemetry/ingest", response_model=IngestResponse, summary="Ingest telemetry packet (Simulated or Real)")
def ingest_telemetry_packet(packet: TelemetryPacket):
    """
    Ingests continuous sensor packet from telemetry stream.
    Validates packet CRC, assesses signal quality, checks deterministic safety rules (<1ms),
    evaluates Scikit-learn Isolation Forest anomaly score, and stores accepted telemetry in SQLite.
    """
    # 1. Evaluate stream reliability & sequence continuity (Module 3)
    reliability = telemetry_reliability_tracker.evaluate_packet_reliability(packet)
    if reliability["is_duplicate"]:
        logger.info(f"Duplicate telemetry packet #{packet.packet_id} for {packet.astronaut_id} filtered.")

    # 2. Fetch astronaut baselines from database to compare deviations accurately
    hr_baseline = 65.0
    temp_baseline = 36.6
    hrv_baseline = 55.0
    sleep_debt = 0.5
    latency_drift = 0.0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT vitals FROM astronauts WHERE id = ?;", (packet.astronaut_id,))
        row = cursor.fetchone()
        if row and row["vitals"]:
            v = json.loads(row["vitals"])
            hr_baseline = float(v.get("heartRateBaseline", 65.0))
            temp_baseline = float(v.get("tempBaseline", 36.6))
            hrv_baseline = float(v.get("hrvBaseline", 55.0))
            sleep_debt = float(v.get("sleepDebtHours", 0.5))
            latency_drift = float(v.get("cognitiveLatencyDelta_ms", 0.0))

    # Prefer stream values if packet provided them
    hrv = packet.sensor_stream.hrv_ms if packet.sensor_stream.hrv_ms is not None else hrv_baseline
    sleep_debt_eff = packet.sensor_stream.sleep_debt_h if packet.sensor_stream.sleep_debt_h is not None else sleep_debt
    latency_drift_eff = packet.sensor_stream.latency_drift_ms if packet.sensor_stream.latency_drift_ms is not None else latency_drift

    # 2. Evaluate event through decision engine
    assessment = assess_telemetry_event(
        astronaut_id=packet.astronaut_id,
        vital_reading={
            "heart_rate_bpm": packet.sensor_stream.heart_rate_bpm,
            "spo2_pct": packet.sensor_stream.spo2_pct,
            "skin_temp_c": packet.sensor_stream.skin_temp_c,
            "hrv": hrv,
            "heartRateBaseline": hr_baseline,
            "tempBaseline": temp_baseline,
            "sleepDebtHours": sleep_debt_eff,
            "cognitiveLatencyDelta_ms": latency_drift_eff
        },
        impedance=packet.sensor_stream.impedance_ohms,
        battery=packet.battery_level_pct or 95.0,
        crc_valid=bool(packet.crc32_valid)
    )

    # 3. Persist to SQLite
    with get_db() as conn:
        cursor = conn.cursor()

        # Save raw telemetry entry
        cursor.execute("""
        INSERT INTO telemetry_history (
            packet_id, astronaut_id, timestamp_met, ecg_lead2_mv, spo2_pct,
            heart_rate_bpm, skin_temp_c, imu_accel_g, impedance_ohms,
            battery_level_pct, crc32_valid, quality_status, anomaly_score, is_anomaly
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            packet.packet_id,
            packet.astronaut_id,
            packet.timestamp_met,
            packet.sensor_stream.ecg_lead2_mv,
            packet.sensor_stream.spo2_pct,
            packet.sensor_stream.heart_rate_bpm,
            packet.sensor_stream.skin_temp_c,
            json.dumps(packet.sensor_stream.imu_accel_g),
            packet.sensor_stream.impedance_ohms,
            packet.battery_level_pct,
            1 if packet.crc32_valid else 0,
            assessment["quality_status"],
            assessment["anomaly_score"],
            1 if assessment["is_anomaly"] else 0
        ))

        # Enqueue cloud synchronization for raw telemetry packet
        enqueue_sync_event(
            cursor=cursor,
            entity_type="telemetry_history",
            record_id=str(packet.packet_id),
            operation="INSERT",
            payload={
                "packet_id": packet.packet_id,
                "astronaut_id": packet.astronaut_id,
                "timestamp_met": packet.timestamp_met,
                "ecg_lead2_mv": packet.sensor_stream.ecg_lead2_mv,
                "spo2_pct": packet.sensor_stream.spo2_pct,
                "heart_rate_bpm": packet.sensor_stream.heart_rate_bpm,
                "skin_temp_c": packet.sensor_stream.skin_temp_c,
                "imu_accel_g": packet.sensor_stream.imu_accel_g,
                "impedance_ohms": packet.sensor_stream.impedance_ohms,
                "battery_level_pct": packet.battery_level_pct,
                "crc32_valid": bool(packet.crc32_valid),
                "quality_status": assessment["quality_status"],
                "anomaly_score": assessment["anomaly_score"],
                "is_anomaly": bool(assessment["is_anomaly"]),
                "is_simulated": True
            }
        )

        # Check if astronaut exists and update vitals & condition
        cursor.execute("SELECT vitals, mlModel, condition, conditionSeverity FROM astronauts WHERE id = ?;", (packet.astronaut_id,))
        ast_row = cursor.fetchone()
        if ast_row:
            current_vitals = json.loads(ast_row["vitals"])
            current_vitals["heartRate"] = packet.sensor_stream.heart_rate_bpm
            current_vitals["spo2"] = packet.sensor_stream.spo2_pct
            current_vitals["temperature"] = packet.sensor_stream.skin_temp_c
            current_vitals["hrv"] = hrv
            current_vitals["sleepDebtHours"] = sleep_debt_eff
            current_vitals["cognitiveLatencyDelta_ms"] = int(latency_drift_eff)
            if packet.sensor_stream.respiration_rate:
                current_vitals["respiration"] = packet.sensor_stream.respiration_rate

            current_ml = json.loads(ast_row["mlModel"])
            current_ml["anomalyScore"] = assessment["anomaly_score"]
            current_ml["status"] = assessment["ml_status"]
            current_ml["primaryFactors"] = assessment.get("primary_factors", current_ml.get("primaryFactors", []))

            # Dynamically update condition severity based on assessment
            cond_severity = ast_row["conditionSeverity"]
            cond_label = ast_row["condition"]

            if assessment.get("is_critical"):
                cond_severity = "critical"
                cond_label = assessment.get("safety_alert", "Critical Physiological Outlier")[:35]
            elif assessment.get("safety_severity") == "WARNING" or assessment["anomaly_score"] < -0.2:
                cond_severity = "warning"
                cond_label = "Unusual Pattern (Needs Rest)"
            elif assessment["anomaly_score"] >= 0.0 and cond_severity == "nominal":
                cond_severity = "nominal"
                cond_label = "Healthy"

            cursor.execute("""
            UPDATE astronauts
            SET vitals = ?, mlModel = ?, condition = ?, conditionSeverity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """, (json.dumps(current_vitals), json.dumps(current_ml), cond_label, cond_severity, packet.astronaut_id))

            # Enqueue astronaut profile update to cloud outbox
            enqueue_sync_event(
                cursor=cursor,
                entity_type="astronauts",
                record_id=packet.astronaut_id,
                operation="UPDATE",
                payload={
                    "id": packet.astronaut_id,
                    "condition": cond_label,
                    "conditionSeverity": cond_severity,
                    "vitals": current_vitals,
                    "mlModel": current_ml
                }
            )

        # Trigger automatic health alert if safety rule breached
        if assessment.get("safety_alert"):
            alert_id = f"ALT-{packet.timestamp_met.replace(':', '-')}-{packet.packet_id}"
            cursor.execute("""
            INSERT OR REPLACE INTO health_alerts (
                id, astronaut_id, severity, type, message, status, created_at_met
            ) VALUES (?, ?, ?, ?, ?, 'NEW', ?)
            """, (
                alert_id,
                packet.astronaut_id,
                assessment["safety_severity"],
                "Physiological Safety Rule Violation",
                assessment["safety_alert"],
                packet.timestamp_met
            ))
            logger.warning(f"Safety Alert Generated: {assessment['safety_alert']}")

            # Enqueue health alert to cloud outbox
            enqueue_sync_event(
                cursor=cursor,
                entity_type="health_alerts",
                record_id=alert_id,
                operation="INSERT",
                payload={
                    "id": alert_id,
                    "astronaut_id": packet.astronaut_id,
                    "severity": assessment["safety_severity"],
                    "type": "Physiological Safety Rule Violation",
                    "message": assessment["safety_alert"],
                    "status": "NEW",
                    "created_at_met": packet.timestamp_met
                }
            )

        conn.commit()

    return IngestResponse(
        status="ACCEPTED" if assessment["quality_status"] == "OPTIMAL" else assessment["quality_status"],
        packet_id=packet.packet_id,
        astronaut_id=packet.astronaut_id,
        quality_status=assessment["quality_status"],
        is_anomaly=assessment["is_anomaly"],
        anomaly_score=assessment["anomaly_score"],
        safety_alert=assessment.get("safety_alert"),
        processed_at_met=packet.timestamp_met,
        is_simulated=bool(packet.is_simulated)
    )

@router.get("/telemetry/history/{astronaut_id}", summary="Get recent telemetry history")
def get_telemetry_history(astronaut_id: str, limit: int = 50):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM telemetry_history
        WHERE astronaut_id = ?
        ORDER BY id DESC LIMIT ?;
        """, (astronaut_id, limit))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["imu_accel_g"] = json.loads(d["imu_accel_g"] or "[0,0,0]")
            result.append(d)
        return result

@router.get("/telemetry/latest/{astronaut_id}", summary="Get latest telemetry reading for astronaut")
def get_latest_telemetry(astronaut_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM telemetry_history
        WHERE astronaut_id = ?
        ORDER BY id DESC LIMIT 1;
        """, (astronaut_id,))
        row = cursor.fetchone()
        if not row:
            # Fallback to astronaut vitals
            cursor.execute("SELECT vitals FROM astronauts WHERE id = ?;", (astronaut_id,))
            ast_row = cursor.fetchone()
            if not ast_row:
                raise HTTPException(status_code=404, detail="Astronaut not found.")
            vitals = json.loads(ast_row["vitals"])
            return {
                "packet_id": 0,
                "astronaut_id": astronaut_id,
                "timestamp_met": "142:04:36:18",
                "heart_rate_bpm": vitals.get("heartRate"),
                "spo2_pct": vitals.get("spo2"),
                "skin_temp_c": vitals.get("temperature"),
                "quality_status": "OPTIMAL",
                "is_simulated": True
            }
        d = dict(row)
        d["imu_accel_g"] = json.loads(d["imu_accel_g"] or "[0,0,0]")
        d["is_simulated"] = True
        return d

@router.get("/telemetry/simulator/scenarios", summary="Get supported software simulation scenarios")
def get_simulation_scenarios():
    """
    Returns the supported software telemetry simulation modes:
    - Mode A: Normal Operation
    - Mode B: Fatigue Scenario
    - Mode C: Hypoxia Scenario
    - Mode D: Cardiac Irregularity Scenario
    - Mode E: Custom Simulation
    """
    return list(SIMULATION_SCENARIOS.values())

@router.post("/telemetry/simulator/step", response_model=SimulatorStepResponse, summary="Execute one reproducible software simulation step")
def step_simulation(req: SimulatorStepRequest):
    """
    Core Software Simulator Ingestion Engine:
    1. Generates reproducible synthetic telemetry packet for the specified astronaut and scenario mode.
    2. Exercises the exact same ingestion and validation pipeline as physical sensors.
    3. Evaluates deterministic safety rules and Scikit-learn anomaly score.
    4. Persists the record to SQLite and updates dashboard state in near-real-time.
    5. Clearly labels output as simulated data.
    """
    packet = generate_simulated_packet(
        astronaut_id=req.astronaut_id,
        scenario_mode=req.scenario_mode,
        tick=req.tick,
        custom_params=req.custom_params
    )

    ingest_res = ingest_telemetry_packet(packet)

    return SimulatorStepResponse(
        packet=packet,
        ingest_result=ingest_res,
        scenario_mode=req.scenario_mode.upper(),
        tick=req.tick,
        data_label="SIMULATED TELEMETRY"
    )

@router.post("/telemetry/simulator/reset", summary="Reset simulation history for astronaut")
def reset_simulation_history(astronaut_id: Optional[str] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        if astronaut_id:
            cursor.execute("DELETE FROM telemetry_history WHERE astronaut_id = ?;", (astronaut_id,))
        else:
            cursor.execute("DELETE FROM telemetry_history;")
        conn.commit()
    return {"status": "SIMULATION_TELEMETRY_RESET", "astronaut_id": astronaut_id or "ALL"}

@router.get("/telemetry/stream-health", summary="Get telemetry stream quality and reliability metrics")
def get_telemetry_stream_health():
    """Returns packet count, sequence gaps, duplicates filtered, and quality score."""
    return telemetry_reliability_tracker.get_stream_health()
