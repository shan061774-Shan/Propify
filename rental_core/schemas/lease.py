from pydantic import BaseModel, ConfigDict
from datetime import date
from rental_core.models.lease import LeaseStatus

class LeaseBase(BaseModel):
    start_date: date
    end_date: date | None = None
    unit_id: int
    tenant_id: int

class LeaseCreate(LeaseBase):
    pass

class LeaseUpdate(BaseModel):
    status: LeaseStatus | None = None
    tenant_id: int | None = None
    end_date: date | None = None

class LeaseRead(LeaseCreate):
    id: int
    lease_number: str
    status: LeaseStatus
    model_config = ConfigDict(from_attributes=True)
