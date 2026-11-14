import time
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, status
from app.database.connection import get_db
from app.schemas.incident_schema import Incident, IncidentCreate, IncidentResolveRequest, RecoveryTimeline
from app.database.supabase_client import supabase_manager
from app.services.sync_service import enqueue_sync_event
from app.core.auth import validate_session

router = APIRouter()

@router.get("/incidents", response_model=List[Incident], summary="Get flight log of physiological & environmental incidents")
def get_incidents():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["actionsTaken"] = json.loads(d["actionsTaken"] or "[]")
            result.append(d)
        return result

@router.post("/incidents", summary="Record a new incident in offline ledger")
async def create_incident(inc: IncidentCreate):
    incident_id = f"INC-2026-{int(time.time())}"
    timestamp_met = "MET 142d 04:45:00"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO incidents (
            id, timestamp, severity, type, targetAstronautId, targetAstronautName,
            summary, resolutionStatus, syncStatus, assignedOfficer, actionsTaken
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active - Action Pending', 'Queued for Earth DSN Sync', ?, ?);
        """, (
            incident_id,
            timestamp_met,
            inc.severity,
            inc.type,
            inc.targetAstronautId,
            inc.targetAstronautName,
            inc.summary,
            inc.assignedOfficer,
            json.dumps(inc.actionsTaken)
        ))

        cursor.execute("""
        INSERT INTO audit_logs (user_officer, action, details, timestamp_met)
        VALUES (?, ?, ?, ?);
        """, (
            inc.assignedOfficer,
            "INCIDENT_LOGGED",
            f"Created incident {incident_id} ({inc.type}) for {inc.targetAstronautName}",
            timestamp_met
        ))

        # Enqueue cloud synchronization event for new incident
        enqueue_sync_event(
            cursor=cursor,
            entity_type="incidents",
            record_id=incident_id,
            operation="INSERT",
            payload={
                "id": incident_id,
                "timestamp": timestamp_met,
                "severity": inc.severity,
                "type": inc.type,
                "targetAstronautId": inc.targetAstronautId,
                "targetAstronautName": inc.targetAstronautName,
                "summary": inc.summary,
                "resolutionStatus": "Active - Action Pending",
                "syncStatus": "Queued for Earth DSN Sync",
                "assignedOfficer": inc.assignedOfficer,
                "actionsTaken": inc.actionsTaken
            }
        )

        conn.commit()

    # Attempt Supabase sync if online and configured
    sync_result = await supabase_manager.sync_incident({
        "id": incident_id,
        "timestamp": timestamp_met,
        "severity": inc.severity,
        "type": inc.type,
        "targetAstronautId": inc.targetAstronautId,
        "targetAstronautName": inc.targetAstronautName,
        "summary": inc.summary,
        "resolutionStatus": "Active - Action Pending",
        "syncStatus": "Queued for Earth DSN Sync",
        "assignedOfficer": inc.assignedOfficer,
        "actionsTaken": inc.actionsTaken
    })

    return {
        "status": "RECORDED_LOCALLY",
        "incident_id": incident_id,
        "sync_status": sync_result.get("status", "CACHED_LOCALLY"),
        "timestamp": timestamp_met
    }

@router.patch("/incidents/{incident_id}/resolve", summary="Resolve mission incident with notes")
def resolve_incident(
    incident_id: str,
    req: IncidentResolveRequest,
    authorization: Optional[str] = Header(None)
):
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        session = validate_session(token)
        if session and session.get("role") == "student":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Student role is not authorized to resolve mission incidents."
            )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?;", (incident_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found.")

        actions = json.loads(row["actionsTaken"] or "[]")
        actions.append(f"Resolved by {req.resolved_by}: {req.resolution_notes}")

        cursor.execute("""
        UPDATE incidents
        SET resolutionStatus = 'Resolved',
            actionsTaken = ?,
            syncStatus = 'Queued for Earth DSN Sync'
        WHERE id = ?;
        """, (json.dumps(actions), incident_id))

        met_time = "MET 142d 05:08:00"
        cursor.execute("""
        INSERT INTO audit_logs (user_officer, action, details, timestamp_met)
        VALUES (?, ?, ?, ?);
        """, (
            req.resolved_by,
            "INCIDENT_RESOLVED",
            f"Resolved incident {incident_id}: {req.resolution_notes}",
            met_time
        ))

        # Enqueue cloud synchronization event for incident resolution
        enqueue_sync_event(
            cursor=cursor,
            entity_type="incidents",
            record_id=incident_id,
            operation="UPDATE",
            payload={
                "id": incident_id,
                "resolutionStatus": "Resolved",
                "actionsTaken": actions,
                "syncStatus": "Queued for Earth DSN Sync"
            }
        )

        conn.commit()

    return {
        "status": "RESOLVED",
        "incident_id": incident_id,
        "resolution_status": "Resolved",
        "resolved_by": req.resolved_by
    }

@router.get("/recovery", response_model=List[RecoveryTimeline], summary="Get active crew recovery trajectories")
def get_recovery_timelines():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recovery_timelines;")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
