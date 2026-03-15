from pydantic import BaseModel
from datetime import date
from pydantic import ConfigDict
from rental_core.models.maintenance import MaintenanceStatus

class MaintenanceCreate(BaseModel):
    unit_id: int
    description: str
    priority: str = "low"
    status: MaintenanceStatus = MaintenanceStatus.pending
    assigned_to: str | None = ""
    contractor_id: int | None = None
    photo_path: str | None = None
    request_date: date | None = None

class MaintenanceUpdate(BaseModel):
    status: MaintenanceStatus | None = None
    assigned_to: str | None = None
    contractor_id: int | None = None
    priority: str | None = None
    photo_path: str | None = None
    closed_date: date | None = None

class MaintenanceRead(MaintenanceCreate):
    id: int
    closed_date: date | None = None
    model_config = ConfigDict(from_attributes=True)
