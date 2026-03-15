from pydantic import BaseModel

class PropertyBase(BaseModel):
    name: str
    address: str
    grace_period_days: int = 3
    late_fee_amount: int = 30

class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    grace_period_days: int | None = None
    late_fee_amount: int | None = None

class PropertyRead(PropertyBase):
    id: int

    class Config:
        from_attributes = True
