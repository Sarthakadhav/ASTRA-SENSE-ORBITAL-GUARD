from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from app.services.sync_service import sync_service
from app.schemas.sync_schema import (
    SyncStatusResponse, SyncTriggerResponse, SyncMetricsResponse,
    ConflictResolutionRequest, OutboxItem
)
from app.database.connection import get_db
from app.core.auth import validate_session

router = APIRouter()

@router.get("/sync/status", response_model=SyncStatusResponse, summary="Get cloud synchronization pipeline status")
async def get_synchronization_status():
    """Returns operational status of local SQLite to Supabase cloud sync."""
    return await sync_service.get_sync_status()

@router.get("/sync/metrics", response_model=SyncMetricsResponse, summary="Get high-resolution sync observability metrics")
async def get_synchronization_metrics():
    """Returns real-time queue metrics, latency, backlog percent, and system health."""
    return await sync_service.get_sync_metrics()

@router.post("/sync/trigger", response_model=SyncTriggerResponse, summary="Trigger manual cloud synchronization batch")
async def trigger_synchronization():
    """Processes pending outbox items and attempts upload to Supabase."""
    res = await sync_service.process_sync_batch()
    return SyncTriggerResponse(
        status=res.get("status", "COMPLETED"),
        processed=res.get("processed", 0),
        synced=res.get("synced", 0),
        failed=res.get("failed", 0),
        message=res.get("message")
    )

@router.post("/sync/retry", summary="Reset failed outbox events for retry")
async def retry_failed_synchronization():
    """Resets failed and retry outbox records back to PENDING."""
    return await sync_service.retry_failed_events()

@router.get("/sync/conflicts", summary="List unresolved synchronization conflicts")
async def list_conflicts():
    """Returns all synchronization conflicts flagged for human resolution."""
    return await sync_service.get_conflicts()

@router.post("/sync/conflicts/resolve", summary="Resolve a synchronization conflict")
async def resolve_conflict_endpoint(
    req: ConflictResolutionRequest,
    authorization: Optional[str] = Header(None)
):
    """Marks a conflict resolved with defined choice."""
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        session = validate_session(token)
        if session and session.get("role") == "student":
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Student role is not authorized to resolve synchronization conflicts."
            )
        if session and "name" in session:
            req.resolved_by = session["name"]

    if req.resolution_choice not in ("RESOLVED_LOCAL", "RESOLVED_CLOUD", "RESOLVED_MERGE"):
        raise HTTPException(
            status_code=400,
            detail="Invalid resolution choice. Must be RESOLVED_LOCAL, RESOLVED_CLOUD, or RESOLVED_MERGE."
        )
    return await sync_service.resolve_conflict(
        conflict_id=req.conflict_id,
        resolution_choice=req.resolution_choice,
        resolved_by=req.resolved_by
    )

@router.get("/sync/outbox", summary="Inspect recent outbox queue events")
def list_outbox_events(limit: int = 50):
    """Inspects local SQLite outbox queue."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, entity_type, record_id, operation, status, attempt_count,
               created_at, last_attempt_at, next_retry_at, error_info
        FROM cloud_sync_outbox
        ORDER BY created_at DESC
        LIMIT ?;
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

