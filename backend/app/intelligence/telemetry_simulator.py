import math
import random
import json
from typing import Dict, Any, Optional
from app.schemas.telemetry_schema import TelemetryPacket, SensorStreamData, IngestResponse
from app.database.connection import get_db

SIMULATION_SCENARIOS = {
    "NORMAL": {
        "id": "NORMAL",
        "name": "Mode A — Normal Operation",
        "description": "Stable physiological readings representing a healthy astronaut at nominal baseline in microgravity.",
        "target_vitals": {
            "hr_offset": 0.0,
            "spo2": 98.6,
            "hrv": 58.0,
            "temp": 36.6,
            "sleep_debt": 0.5,
            "latency_drift": 0.0,
            "impedance": 480.0
        }
    },
    "FATIGUE": {
        "id": "FATIGUE",
        "name": "Mode B — Fatigue Scenario",
        "description": "Cumulative sleep deficit, reduced HRV recovery, resting pulse drift, and psychomotor cognitive latency slowdown (+185ms).",
        "target_vitals": {
            "hr_offset": 18.0,
            "spo2": 96.5,
            "hrv": 23.0,
            "temp": 37.1,
            "sleep_debt": 6.4,
            "latency_drift": 185.0,
            "impedance": 510.0
        }
    },
    "HYPOXIA": {
        "id": "HYPOXIA",
        "name": "Mode C — Hypoxia Scenario",
        "description": "Controlled abnormal SpO2 drop (<88%) and compensatory tachycardia to exercise deterministic safety alerting and SOP-HYPOXIA-02 retrieval.",
        "target_vitals": {
            "hr_offset": 28.0,
            "spo2": 85.5,
            "hrv": 28.0,
            "temp": 36.7,
            "sleep_debt": 1.2,
            "latency_drift": 45.0,
            "impedance": 490.0
        }
    },
    "CARDIAC": {
        "id": "CARDIAC",
        "name": "Mode D — Cardiac Irregularity Scenario",
        "description": "Acute sustained tachycardia (>130 bpm) with depressed HRV and ectopic Lead-II ECG waveform to test arrhythmia safety thresholds and SOP-ARRHYTHMIA-03.",
        "target_vitals": {
            "hr_offset": 62.0,
            "spo2": 95.0,
            "hrv": 16.0,
            "temp": 37.3,
            "sleep_debt": 2.0,
            "latency_drift": 70.0,
            "impedance": 520.0
        }
    },
    "CUSTOM": {
        "id": "CUSTOM",
        "name": "Mode E — Custom Simulation",
        "description": "User-configured physiological parameters and sensor noise bounds to test specific clinical decision support workflows.",
        "target_vitals": {}
    }
}

def generate_ecg_sample(phase: float, mode: str) -> float:
    """
    Computes a synthetic Lead-II ECG potential (mV) based on P-Q-R-S-T wave model.
    phase: 0.0 to 1.0 within cardiac cycle.
    """
    # Baseline
    val = 0.0
    # P wave (at phase 0.15)
    val += 0.15 * math.exp(-((phase - 0.15) ** 2) / 0.002)
    # Q wave (at phase 0.28)
    val -= 0.15 * math.exp(-((phase - 0.28) ** 2) / 0.0005)
    # R peak (at phase 0.32)
    r_height = 1.35 if mode != "CARDIAC" else 1.85
    val += r_height * math.exp(-((phase - 0.32) ** 2) / 0.0008)
    # S wave (at phase 0.36)
    val -= 0.30 * math.exp(-((phase - 0.36) ** 2) / 0.0008)
    # T wave (at phase 0.55)
    t_height = 0.28 if mode != "CARDIAC" else 0.45
    val += t_height * math.exp(-((phase - 0.55) ** 2) / 0.006)

    if mode == "CARDIAC":
        # Add ectopic irritability artifact
        val += 0.20 * math.sin(phase * 4 * math.pi)

    return round(val, 3)

def generate_simulated_packet(
    astronaut_id: str = "AST-01",
    scenario_mode: str = "NORMAL",
    tick: int = 0,
    custom_params: Optional[Dict[str, Any]] = None
) -> TelemetryPacket:
    """
    Produces a valid, reproducible, deterministic TelemetryPacket.
    Clearly marks data as simulated with reproducible seeds.
    """
    mode = scenario_mode.upper()
    if mode not in SIMULATION_SCENARIOS:
        mode = "NORMAL"

    # Fetch astronaut baseline from SQLite
    hr_baseline = 65.0
    spo2_baseline = 99.0
    temp_baseline = 36.6
    hrv_baseline = 55.0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT vitals FROM astronauts WHERE id = ?;", (astronaut_id,))
        row = cursor.fetchone()
        if row and row["vitals"]:
            v = json.loads(row["vitals"])
            hr_baseline = float(v.get("heartRateBaseline", 65.0))
            spo2_baseline = float(v.get("spo2Baseline", 99.0))
            temp_baseline = float(v.get("tempBaseline", 36.6))
            hrv_baseline = float(v.get("hrvBaseline", 55.0))

    # Deterministic sinusoidal micro-jitter based on tick
    t = float(tick)
    jitter_hr = 1.2 * math.sin(t * 0.4)
    jitter_spo2 = 0.3 * math.cos(t * 0.25)
    jitter_temp = 0.04 * math.sin(t * 0.15)
    jitter_hrv = 1.5 * math.cos(t * 0.35)

    if mode == "NORMAL":
        hr = round(hr_baseline + jitter_hr, 1)
        spo2 = min(100.0, max(97.0, round(spo2_baseline + jitter_spo2, 1)))
        temp = round(temp_baseline + jitter_temp, 2)
        hrv = max(45.0, round(hrv_baseline + jitter_hrv, 1))
        sleep_debt = 0.5
        latency_drift = round(5.0 * math.sin(t * 0.2), 0)
        respiration = round(14.0 + 0.8 * math.sin(t * 0.1), 1)
        impedance = 480.0 + 10.0 * math.sin(t * 0.5)

    elif mode == "FATIGUE":
        # Progressive ramp up of fatigue over ticks if tick is low, settling to steady state
        ramp = min(1.0, 0.5 + (t % 50) / 100.0)
        hr = round(hr_baseline + 18.0 * ramp + jitter_hr, 1)
        spo2 = round(96.4 + jitter_spo2, 1)
        temp = round(37.1 + jitter_temp, 2)
        hrv = max(18.0, round(24.0 + jitter_hrv, 1))
        sleep_debt = round(6.4 + (t % 10) * 0.05, 1)
        latency_drift = round(185.0 + 15.0 * math.sin(t * 0.3), 0)
        respiration = round(17.5 + 1.2 * math.sin(t * 0.2), 1)
        impedance = 510.0

    elif mode == "HYPOXIA":
        # Controlled hypoxic desaturation
        # Progresses from 95% -> 88% -> 84%
        cycle = (t % 40)
        if cycle < 15:
            target_spo2 = 93.0 - (cycle * 0.5)
        elif cycle < 30:
            target_spo2 = 85.5 + math.sin(cycle) * 0.5
        else:
            target_spo2 = 84.0 + math.cos(cycle) * 0.4

        spo2 = round(max(78.0, min(95.0, target_spo2)), 1)
        # Compensatory tachycardia
        hr = round(hr_baseline + 28.0 + jitter_hr, 1)
        temp = round(temp_baseline + jitter_temp, 2)
        hrv = max(20.0, round(30.0 + jitter_hrv, 1))
        sleep_debt = 1.0
        latency_drift = 45.0
        respiration = round(22.0 + 2.0 * math.sin(t * 0.3), 1)
        impedance = 490.0

    elif mode == "CARDIAC":
        # Tachycardia / Arrhythmia
        hr = round(132.0 + 6.0 * math.sin(t * 0.6), 1)
        spo2 = round(95.2 + jitter_spo2, 1)
        temp = round(37.2 + jitter_temp, 2)
        hrv = max(12.0, round(16.0 + jitter_hrv, 1))
        sleep_debt = 2.0
        latency_drift = 65.0
        respiration = round(20.0 + 1.5 * math.sin(t * 0.2), 1)
        impedance = 520.0

    elif mode == "CUSTOM" and custom_params:
        hr = float(custom_params.get("heart_rate_bpm", hr_baseline))
        spo2 = float(custom_params.get("spo2_pct", spo2_baseline))
        temp = float(custom_params.get("skin_temp_c", temp_baseline))
        hrv = float(custom_params.get("hrv_ms", hrv_baseline))
        sleep_debt = float(custom_params.get("sleep_debt_h", 0.0))
        latency_drift = float(custom_params.get("latency_drift_ms", 0.0))
        respiration = float(custom_params.get("respiration_rate", 14.0))
        impedance = float(custom_params.get("impedance_ohms", 480.0))
    else:
        # Fallback to normal
        hr = hr_baseline
        spo2 = spo2_baseline
        temp = temp_baseline
        hrv = hrv_baseline
        sleep_debt = 0.5
        latency_drift = 0.0
        respiration = 14.0
        impedance = 480.0

    # Cardiac phase for ECG
    heart_rate_safe = max(30.0, hr)
    cycle_duration_s = 60.0 / heart_rate_safe
    phase = (t * 0.2) % cycle_duration_s / cycle_duration_s
    ecg_mv = generate_ecg_sample(phase, mode)

    # MET formatted timestamp
    # Base MET day 142, hours 04, minutes (36 + tick//60), seconds (tick % 60)
    met_mins = 36 + (tick // 60)
    met_secs = tick % 60
    met_hours = 4 + (met_mins // 60)
    met_mins = met_mins % 60
    met_str = f"142:{met_hours:02d}:{met_mins:02d}:{met_secs:02d}"

    imu_accel = [
        round(0.02 + 0.01 * math.sin(t * 0.7), 3),
        round(0.04 + 0.02 * math.cos(t * 0.5), 3),
        round(0.01 + 0.01 * math.sin(t * 0.9), 3)
    ]
    if mode == "FATIGUE":
        imu_accel[0] += 0.05

    sensor_data = SensorStreamData(
        ecg_lead2_mv=ecg_mv,
        spo2_pct=spo2,
        heart_rate_bpm=hr,
        skin_temp_c=temp,
        imu_accel_g=imu_accel,
        impedance_ohms=impedance,
        hrv_ms=hrv,
        sleep_debt_h=sleep_debt,
        latency_drift_ms=latency_drift,
        respiration_rate=respiration
    )

    return TelemetryPacket(
        packet_id=142000 + tick,
        timestamp_met=met_str,
        astronaut_id=astronaut_id,
        sensor_stream=sensor_data,
        battery_level_pct=94.0,
        crc32_valid=True,
        device_id=f"SIM-ESP32-{astronaut_id}",
        is_simulated=True
    )


class TelemetryStreamReliabilityTracker:
    """
    Module 3: Aerospace Telemetry Stream Quality & Reliability Engine.
    Detects dropped packets (sequence gaps), duplicate transmissions,
    and timestamp jitter across high-frequency physiological telemetry.
    """
    def __init__(self):
        self.last_packet_ids: Dict[str, int] = {}
        self.total_packets_received: int = 0
        self.sequence_gaps_count: int = 0
        self.duplicates_dropped_count: int = 0
        self.jitter_violations_count: int = 0
        self.anomalies_flagged_count: int = 0

    def evaluate_packet_reliability(self, packet: TelemetryPacket) -> Dict[str, Any]:
        """
        Validates packet sequence continuity and integrity.
        Returns health assessment for the incoming frame.
        """
        self.total_packets_received += 1
        ast_id = packet.astronaut_id
        pkt_id = packet.packet_id
        is_duplicate = False
        gap_detected = None
        jitter_warning = None

        if ast_id in self.last_packet_ids:
            last_id = self.last_packet_ids[ast_id]
            if pkt_id == last_id:
                is_duplicate = True
                self.duplicates_dropped_count += 1
            elif pkt_id < last_id:
                # Out of order or loop packet
                is_duplicate = True
                self.duplicates_dropped_count += 1
            elif pkt_id > last_id + 1:
                gap_size = pkt_id - last_id - 1
                gap_detected = gap_size
                self.sequence_gaps_count += gap_size

        self.last_packet_ids[ast_id] = pkt_id

        # Jitter validation on cognitive latency or sample clock
        if packet.sensor_stream and packet.sensor_stream.latency_drift_ms is not None:
            if packet.sensor_stream.latency_drift_ms > 2500.0:
                jitter_warning = f"Clock drift/jitter exceeded 2500ms ({packet.sensor_stream.latency_drift_ms}ms)"
                self.jitter_violations_count += 1

        quality_factor = 100.0
        if self.total_packets_received > 0:
            loss_ratio = (self.sequence_gaps_count + self.duplicates_dropped_count) / self.total_packets_received
            quality_factor = max(0.0, min(100.0, round((1.0 - loss_ratio) * 100, 2)))

        return {
            "is_duplicate": is_duplicate,
            "sequence_gap": gap_detected,
            "jitter_warning": jitter_warning,
            "stream_quality_pct": quality_factor,
            "status": "DUPLICATE_DROPPED" if is_duplicate else ("GAP_DETECTED" if gap_detected else "STREAM_NOMINAL")
        }

    def get_stream_health(self) -> Dict[str, Any]:
        """Returns cumulative stream health metrics."""
        quality_factor = 100.0
        if self.total_packets_received > 0:
            loss_ratio = (self.sequence_gaps_count + self.duplicates_dropped_count) / self.total_packets_received
            quality_factor = max(0.0, min(100.0, round((1.0 - loss_ratio) * 100, 2)))

        return {
            "total_packets_received": self.total_packets_received,
            "sequence_gaps_count": self.sequence_gaps_count,
            "duplicates_dropped_count": self.duplicates_dropped_count,
            "jitter_violations_count": self.jitter_violations_count,
            "anomalies_flagged_count": self.anomalies_flagged_count,
            "stream_quality_score": quality_factor,
            "stream_status": "EXCELLENT" if quality_factor >= 95.0 else ("DEGRADED" if quality_factor >= 80.0 else "UNSTABLE")
        }

# Global singleton tracker
telemetry_reliability_tracker = TelemetryStreamReliabilityTracker()

