from typing import Optional, List
from pydantic import BaseModel, Field

class IncidentCreate(BaseModel):
    severity: str = Field(..., description="CRITICAL | WARNING | ADVISORY | NOMINAL")
    type: str
    targetAstronautId: str
    targetAstronautName: str
    summary: str
    assignedOfficer: str = "Cmdr. Sarah Chen"
    actionsTaken: List[str] = Field(default_factory=list)

class IncidentResolveRequest(BaseModel):
    resolution_notes: str = Field(..., description="Details regarding incident resolution")
    resolved_by: str = Field(default="Cmdr. Sarah Chen", description="Officer signing off")

class IncidentItem(BaseModel):
    id: str
    timestamp: str
    severity: str
    type: str
    targetAstronautId: str
    targetAstronautName: str
    summary: str
    resolutionStatus: str
    syncStatus: str
    assignedOfficer: str
    actionsTaken: List[str]

# Backward compatibility alias
Incident = IncidentItem

class RecoveryTimeline(BaseModel):
    astronautId: str
    name: str
    protocol: str
    currentStep: str
    progressPercent: int
    projectedFullRecoveryMET: str
    sleepDebtTarget: str
    exercisePermitted: str
    circadianLightProfile: str

class DSNSyncResponse(BaseModel):
    status: str
    queued_events_count: int
    synced_events_count: int
    latency_seconds: int
    dsn_station: str = "Goldstone DSN Antenna 14"
    details: str

class DSNQueueItem(BaseModel):
    id: str
    type: str
    timestamp: str
    summary: str
    sync_status: str
