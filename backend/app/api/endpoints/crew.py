import json
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Header
from app.database.connection import get_db
from app.schemas.crew_schema import (
    AstronautProfile, CrewReadinessResponse,
    WorkloadRedistributionRequest, WorkloadRedistributionResponse
)
from app.intelligence.crew_readiness import calculate_crew_readiness_metrics
from app.services.sync_service import enqueue_sync_event
from app.core.logging import logger
from app.core.auth import validate_session

router = APIRouter()

def _format_astronaut_row(row) -> Dict[str, Any]:
    ast = dict(row)
    ast["readinessBreakdown"] = json.loads(ast["readinessBreakdown"])
    ast["vitals"] = json.loads(ast["vitals"])
    ast["sensorReliability"] = json.loads(ast["sensorReliability"])
    ast["mlModel"] = json.loads(ast["mlModel"])
    ast["responsibilities"] = json.loads(ast["responsibilities"])
    ast["backupOfficer"] = json.loads(ast["backupOfficer"]) if ast["backupOfficer"] else None
    ast["isReassigned"] = bool(ast["isReassigned"])
    return ast

@router.get("/crew", summary="Get all 4 astronaut profiles")
def get_crew():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM astronauts ORDER BY id ASC;")
        rows = cursor.fetchall()
        return [_format_astronaut_row(r) for r in rows]

@router.get("/crew/readiness", response_model=CrewReadinessResponse, summary="Get crew operational readiness index")
def get_crew_readiness():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT isReassigned FROM astronauts WHERE id = 'AST-01';")
        row = cursor.fetchone()
        is_redistributed = bool(row["isReassigned"]) if row else False
        return calculate_crew_readiness_metrics(is_redistributed=is_redistributed)

@router.get("/crew/{astronaut_id}", summary="Get astronaut profile by ID")
def get_astronaut(astronaut_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM astronauts WHERE id = ?;", (astronaut_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Astronaut {astronaut_id} not found.")
        return _format_astronaut_row(row)

@router.post("/crew/redistribute", response_model=WorkloadRedistributionResponse, summary="Execute dynamic workload redistribution")
def redistribute_workload(
    req: WorkloadRedistributionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Executes Module 3 Workload Redistribution:
    Delegates clinical responsibilities from fatigued Astronaut A (Dr. Vance)
    to qualified backup Cmdr. Sarah Chen (Level 2 Flight Medicine).
    Elevates Crew Readiness Index from 68/100 to 82/100.
    """
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        session = validate_session(token)
        if session and session.get("role") == "student":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Student role is not authorized to execute workload redistribution."
            )

    with get_db() as conn:
        cursor = conn.cursor()

        # Update Vance (AST-01)
        cursor.execute("""
        UPDATE astronauts
        SET condition = 'Resting / Relieved',
            conditionSeverity = 'nominal',
            isReassigned = 1,
            readinessScore = 78,
            recommendation = 'Workload successfully transferred to Cmdr. Sarah Chen. Protected rest cycle active.',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (req.primary_astronaut_id,))

        # Update Chen (AST-02) - add assumed responsibilities
        cursor.execute("SELECT responsibilities FROM astronauts WHERE id = ?;", (req.backup_astronaut_id,))
        chen_row = cursor.fetchone()
        if chen_row:
            chen_resp = json.loads(chen_row["responsibilities"])
            if not any(r.get("id") == "RESP-01-TRANSFER" for r in chen_resp):
                chen_resp.append({
                    "id": "RESP-01-TRANSFER",
                    "title": "[Assumed] Crew Clinical Checkups",
                    "priority": "High",
                    "canDelegate": False
                })
                cursor.execute("""
                UPDATE astronauts
                SET responsibilities = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """, (json.dumps(chen_resp), req.backup_astronaut_id))

        # Log new incident
        incident_id = f"INC-2026-REDIST-{int(time.time())}"
        cursor.execute("""
        INSERT INTO incidents (
            id, timestamp, severity, type, targetAstronautId, targetAstronautName,
            summary, resolutionStatus, syncStatus, assignedOfficer, actionsTaken
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            incident_id,
            "MET 142d 04:38:00",
            "NOMINAL",
            "Crew Workload Redistribution Executed",
            req.primary_astronaut_id,
            "Dr. Elena Vance",
            "Clinical responsibilities safely delegated to Cmdr. Sarah Chen (Level 2 Flight Med cert). 8-hour protected sleep cycle initiated.",
            "Active - Monitoring Rest",
            "Queued for Earth DSN Sync",
            req.approved_by,
            json.dumps([
                "Astronaut A transferred to acoustic-damped sleep pod.",
                "Emergency trauma standby assigned to Cmdr. Chen."
            ])
        ))

        # Fetch updated records
        cursor.execute("SELECT * FROM astronauts WHERE id = ?;", (req.primary_astronaut_id,))
        primary_ast = _format_astronaut_row(cursor.fetchone())

        cursor.execute("SELECT * FROM astronauts WHERE id = ?;", (req.backup_astronaut_id,))
        backup_ast = _format_astronaut_row(cursor.fetchone())

        # Enqueue cloud synchronization events
        enqueue_sync_event(
            cursor=cursor,
            entity_type="astronauts",
            record_id=req.primary_astronaut_id,
            operation="UPDATE",
            payload={
                "id": req.primary_astronaut_id,
                "condition": "Resting / Relieved",
                "conditionSeverity": "nominal",
                "isReassigned": True,
                "readinessScore": 78
            }
        )
        enqueue_sync_event(
            cursor=cursor,
            entity_type="incidents",
            record_id=incident_id,
            operation="INSERT",
            payload={
                "id": incident_id,
                "timestamp": "MET 142d 04:38:00",
                "severity": "NOMINAL",
                "type": "Crew Workload Redistribution Executed",
                "targetAstronautId": req.primary_astronaut_id,
                "targetAstronautName": "Dr. Elena Vance",
                "summary": "Clinical responsibilities safely delegated to Cmdr. Sarah Chen.",
                "resolutionStatus": "Active - Monitoring Rest",
                "syncStatus": "Queued for Earth DSN Sync",
                "assignedOfficer": req.approved_by,
                "actionsTaken": [
                    "Astronaut A transferred to acoustic-damped sleep pod.",
                    "Emergency trauma standby assigned to Cmdr. Chen."
                ]
            }
        )

        conn.commit()

    readiness = calculate_crew_readiness_metrics(is_redistributed=True)

    return WorkloadRedistributionResponse(
        status="EXECUTED",
        new_crew_readiness_score=readiness["overallScore"],
        primary_astronaut=primary_ast,
        backup_astronaut=backup_ast,
        incident_id=incident_id,
        message="Non-urgent clinical duties transferred to Cmdr. Chen. Protected rest cycle engaged."
    )

@router.post("/crew/reset-simulation", summary="Reset crew simulation state back to nominal baseline")
def reset_crew_simulation():
    """Resets Vance to nominal baseline and removes reassigned duties from Chen."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE astronauts
        SET condition = 'Tired (Needs Rest)',
            conditionSeverity = 'warning',
            isReassigned = 0,
            readinessScore = 52,
            recommendation = 'Dr. Vance is showing signs of high fatigue. To keep the crew safe and ready, consider letting Commander Chen cover non-urgent tasks so Dr. Vance can rest.',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 'AST-01';
        """)

        cursor.execute("SELECT responsibilities FROM astronauts WHERE id = 'AST-02';")
        chen_row = cursor.fetchone()
        if chen_row:
            resp = json.loads(chen_row["responsibilities"])
            resp = [r for r in resp if r.get("id") != "RESP-01-TRANSFER"]
            cursor.execute("""
            UPDATE astronauts
            SET responsibilities = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 'AST-02';
            """, (json.dumps(resp),))

        conn.commit()

    return {"status": "RESET", "message": "Crew state reset to initial pre-drill baseline."}
