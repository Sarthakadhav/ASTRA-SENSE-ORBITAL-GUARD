from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class SyncStatusResponse(BaseModel):
    pipeline_state: str
    status_label: str
    message: str
    cloud_configured: bool
    cloud_connected: bool
    cloud_status: str
    pending_count: int
    synced_count: int
    failed_count: int
    retry_count: int
    unresolved_conflicts: int
    last_successful_sync: Optional[str] = None
    last_error: Optional[str] = None
    outbox_summary: Dict[str, int] = Field(default_factory=dict)

class SyncTriggerResponse(BaseModel):
    status: str
    processed: int
    synced: int
    failed: int
    message: Optional[str] = None

class SyncMetricsResponse(BaseModel):
    total_outbox_events: int
    synced_events: int
    pending_events: int
    retry_events: int
    failed_events: int
    dead_letter_events: int
    unresolved_conflicts: int
    outbox_backlog_pct: float
    system_health_score: float
    cloud_connected: bool
    cloud_status: str
    latency_ms: float = 12.4
    protocol: str = "PostgREST / HTTPS"

class ConflictResolutionRequest(BaseModel):
    conflict_id: str
    resolution_choice: str = Field(..., description="RESOLVED_LOCAL | RESOLVED_CLOUD | RESOLVED_MERGE")
    resolved_by: str = Field(default="Flight Surgeon Dr. Robert Vance")

class OutboxItem(BaseModel):
    id: str
    entity_type: str
    record_id: str
    operation: str
    status: str
    attempt_count: int
    created_at: str
    last_attempt_at: Optional[str] = None
    next_retry_at: Optional[str] = None
    error_info: Optional[str] = None

