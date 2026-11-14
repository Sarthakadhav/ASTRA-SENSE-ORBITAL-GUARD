from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SensorStreamData(BaseModel):
    ecg_lead2_mv: float = Field(..., description="ECG Lead-II potential in millivolts")
    spo2_pct: float = Field(..., ge=0, le=100, description="Blood oxygen saturation percentage")
    heart_rate_bpm: float = Field(..., ge=0, le=300, description="Heart rate in beats per minute")
    skin_temp_c: float = Field(..., description="Skin / core temperature in degrees Celsius")
    imu_accel_g: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], description="3-axis accelerometer readings [x, y, z]")
    impedance_ohms: float = Field(default=480.0, description="Electrode contact impedance")
    hrv_ms: Optional[float] = Field(default=None, description="Heart Rate Variability (RMSSD) in ms")
    sleep_debt_h: Optional[float] = Field(default=None, description="Cumulative 72-hour sleep debt in hours")
    latency_drift_ms: Optional[float] = Field(default=None, description="Psychomotor reaction latency delta in ms")
    respiration_rate: Optional[float] = Field(default=None, description="Respiration breaths per minute")

class TelemetryPacket(BaseModel):
    packet_id: int = Field(..., description="Unique incremental sequence packet ID")
    timestamp_met: str = Field(..., description="Mission Elapsed Time, e.g. 142:04:36:18")
    astronaut_id: str = Field(..., description="Astronaut ID, e.g. AST-01")
    sensor_stream: SensorStreamData
    battery_level_pct: Optional[float] = Field(default=95.0, description="ESP32 battery level")
    crc32_valid: Optional[bool] = Field(default=True, description="CRC32 integrity status")
    device_id: Optional[str] = Field(default="ESP32-BIO-01", description="Hardware device ID")
    is_simulated: bool = Field(default=True, description="Clear indicator whether packet is simulated data")

class IngestResponse(BaseModel):
    status: str
    packet_id: int
    astronaut_id: str
    quality_status: str
    is_anomaly: bool
    anomaly_score: float
    safety_alert: Optional[str] = None
    processed_at_met: str
    is_simulated: bool = Field(default=True, description="Distinguishes simulated from real measurements")

class SimulatorStepRequest(BaseModel):
    astronaut_id: str = Field(default="AST-01", description="Target astronaut profile ID")
    scenario_mode: str = Field(default="NORMAL", description="NORMAL | FATIGUE | HYPOXIA | CARDIAC | CUSTOM")
    tick: int = Field(default=0, ge=0, description="Simulation step counter for reproducible progression")
    custom_params: Optional[Dict[str, Any]] = Field(default=None, description="Custom parameters when in CUSTOM mode")

class SimulatorStepResponse(BaseModel):
    packet: TelemetryPacket
    ingest_result: IngestResponse
    scenario_mode: str
    tick: int
    data_label: str = "SIMULATED TELEMETRY"
