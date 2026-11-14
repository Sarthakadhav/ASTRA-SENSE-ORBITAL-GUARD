import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, status
from app.database.connection import get_db
from app.schemas.inventory_schema import (
    InventoryItem, ConsumeInventoryRequest, EmergencyScenario,
    ReplenishInventoryRequest, CreateInventoryItemRequest, DispensationRecord
)
from app.local_ai.knowledge_base import EMERGENCY_SCENARIOS
from app.services.sync_service import enqueue_sync_event
from app.core.logging import logger
from app.core.auth import validate_session

router = APIRouter()

@router.get("/inventory", response_model=List[InventoryItem], summary="Get medical vault inventory")
def get_inventory():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_inventory ORDER BY category ASC, id ASC;")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.post("/inventory/consume", summary="Dispense medication or equipment")
def consume_inventory(
    req: ConsumeInventoryRequest,
    authorization: Optional[str] = Header(None)
):
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        session = validate_session(token)
        if session and session.get("role") == "student":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Student role is not authorized to dispense medical inventory."
            )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_inventory WHERE id = ?;", (req.item_id,))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Medical item not found.")

        current_stock = item["stock"]
        if current_stock < req.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {item['name']}. Available: {current_stock}, Requested: {req.quantity}"
            )

        new_stock = current_stock - req.quantity
        new_status = item["status"]
        if new_stock <= item["minSafeStock"]:
            new_status = "Low Reserve Warning"

        cursor.execute("""
        UPDATE medical_inventory
        SET stock = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (new_stock, new_status, req.item_id))

        met_time = "MET 142d 04:42:00"

        # Record dispensation entry
        cursor.execute("""
        INSERT INTO inventory_dispensations (
            item_id, item_name, quantity, patient_astronaut_id, reason, authorized_by, timestamp_met
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            req.item_id,
            item["name"],
            req.quantity,
            req.patient_id,
            req.reason,
            req.authorized_by,
            met_time
        ))
        disp_id = cursor.lastrowid

        # Log consumption to audit table
        cursor.execute("""
        INSERT INTO audit_logs (user_officer, action, details, timestamp_met)
        VALUES (?, ?, ?, ?);
        """, (
            req.authorized_by,
            "INVENTORY_DISPENSED",
            f"Dispensed {req.quantity} {item['unit']} of {item['name']} to {req.patient_id or 'Crew'}. Reason: {req.reason}",
            met_time
        ))

        # Enqueue cloud synchronization events
        enqueue_sync_event(
            cursor=cursor,
            entity_type="inventory_dispensations",
            record_id=str(disp_id),
            operation="INSERT",
            payload={
                "id": disp_id,
                "item_id": req.item_id,
                "item_name": item["name"],
                "quantity": req.quantity,
                "patient_astronaut_id": req.patient_id,
                "reason": req.reason,
                "authorized_by": req.authorized_by,
                "timestamp_met": met_time
            }
        )
        enqueue_sync_event(
            cursor=cursor,
            entity_type="medical_inventory",
            record_id=req.item_id,
            operation="DISPENSE",
            payload={
                "transaction_id": f"TX-DISP-{disp_id}",
                "item_id": req.item_id,
                "delta_quantity": -req.quantity,
                "authorized_by": req.authorized_by,
                "patient_id": req.patient_id,
                "timestamp_met": met_time
            }
        )

        conn.commit()

    return {
        "status": "DISPENSED",
        "item_id": req.item_id,
        "item_name": item["name"],
        "dispensed_quantity": req.quantity,
        "remaining_stock": new_stock,
        "inventory_status": new_status,
        "patient": req.patient_id
    }

@router.post("/inventory/replenish", summary="Replenish stock for an inventory item")
def replenish_inventory(req: ReplenishInventoryRequest):
    if req.quantity <= 0:
        raise HTTPException(status_code=400, detail="Replenish quantity must be greater than zero.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_inventory WHERE id = ?;", (req.item_id,))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Medical item not found.")

        new_stock = item["stock"] + req.quantity
        new_status = "Nominal" if new_stock > item["minSafeStock"] else "Low Reserve Warning"

        cursor.execute("""
        UPDATE medical_inventory
        SET stock = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (new_stock, new_status, req.item_id))

        met_time = "MET 142d 04:55:00"
        cursor.execute("""
        INSERT INTO audit_logs (user_officer, action, details, timestamp_met)
        VALUES (?, ?, ?, ?);
        """, (
            req.authorized_by,
            "INVENTORY_REPLENISHED",
            f"Restocked +{req.quantity} {item['unit']} of {item['name']}. Note: {req.notes}",
            met_time
        ))

        # Enqueue cloud synchronization for replenishment
        rep_tx_id = f"TX-REP-{req.item_id}-{int(time.time() * 1000)}"
        enqueue_sync_event(
            cursor=cursor,
            entity_type="medical_inventory",
            record_id=req.item_id,
            operation="REPLENISH",
            payload={
                "transaction_id": rep_tx_id,
                "item_id": req.item_id,
                "delta_quantity": req.quantity,
                "authorized_by": req.authorized_by,
                "timestamp_met": met_time
            }
        )

        conn.commit()

    return {
        "status": "REPLENISHED",
        "item_id": req.item_id,
        "item_name": item["name"],
        "added_quantity": req.quantity,
        "new_stock": new_stock,
        "inventory_status": new_status
    }

@router.post("/inventory/item", summary="Add new medical item to Med Vault")
def create_inventory_item(req: CreateInventoryItemRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM medical_inventory WHERE id = ?;", (req.id,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"Item with ID {req.id} already exists.")

        initial_status = "Nominal" if req.stock > req.minSafeStock else "Low Reserve Warning"

        cursor.execute("""
        INSERT INTO medical_inventory (
            id, category, name, indication, stock, unit, minSafeStock,
            shelfLifeDays, radiationDegradationRate, vitalUrgency, status,
            location, contraindications
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            req.id, req.category, req.name, req.indication, req.stock,
            req.unit, req.minSafeStock, req.shelfLifeDays,
            req.radiationDegradationRate, req.vitalUrgency, initial_status,
            req.location, req.contraindications
        ))

        cursor.execute("""
        INSERT INTO audit_logs (user_officer, action, details, timestamp_met)
        VALUES (?, ?, ?, ?);
        """, (
            "Medical Officer",
            "INVENTORY_ITEM_CREATED",
            f"Added {req.name} ({req.id}) to {req.location}",
            "MET 142d 05:02:00"
        ))

        # Enqueue new inventory item to cloud outbox
        enqueue_sync_event(
            cursor=cursor,
            entity_type="medical_inventory",
            record_id=req.id,
            operation="INSERT",
            payload=req.model_dump()
        )

        conn.commit()

    return {
        "status": "ITEM_CREATED",
        "item_id": req.id,
        "name": req.name,
        "stock": req.stock
    }

@router.get("/inventory/dispensations", response_model=List[DispensationRecord], summary="Get dispensation audit records")
def get_dispensations():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory_dispensations ORDER BY id DESC LIMIT 50;")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.get("/inventory/scenarios", response_model=List[EmergencyScenario], summary="Get simulated emergency supply scenarios")
def get_emergency_scenarios():
    return EMERGENCY_SCENARIOS
