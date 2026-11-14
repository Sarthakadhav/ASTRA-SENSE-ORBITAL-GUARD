from typing import Optional, List
from pydantic import BaseModel, Field

class InventoryItem(BaseModel):
    id: str
    category: str
    name: str
    indication: str
    stock: int
    unit: str
    minSafeStock: int
    shelfLifeDays: int
    radiationDegradationRate: Optional[str] = "0.02%/mo"
    vitalUrgency: str
    status: str
    location: str
    contraindications: Optional[str] = None
    batteryChargePercent: Optional[int] = None

class ScenarioSupplies(BaseModel):
    item: str
    qty: str

class EmergencyScenario(BaseModel):
    id: str
    name: str
    description: str
    requiredSupplies: List[ScenarioSupplies]
    predictedRecoveryHours: float
    crewReadinessImpact: str

class ConsumeInventoryRequest(BaseModel):
    item_id: str
    quantity: int = 1
    reason: str = "Clinical emergency consumption"
    authorized_by: str = "Dr. Elena Vance"
    patient_id: Optional[str] = "AST-01"

class ReplenishInventoryRequest(BaseModel):
    item_id: str
    quantity: int
    authorized_by: str = "Cmdr. Sarah Chen"
    notes: Optional[str] = "Station restock from Cargo Resupply Module"

class CreateInventoryItemRequest(BaseModel):
    id: str
    category: str
    name: str
    indication: str
    stock: int
    unit: str
    minSafeStock: int
    shelfLifeDays: int
    radiationDegradationRate: Optional[str] = "0.02%/mo"
    vitalUrgency: str = "Medium"
    location: str = "Med-Bay Locker D-2"
    contraindications: Optional[str] = None

class DispensationRecord(BaseModel):
    id: int
    item_id: str
    item_name: str
    quantity: int
    patient_astronaut_id: Optional[str] = None
    reason: str
    authorized_by: str
    timestamp_met: str
