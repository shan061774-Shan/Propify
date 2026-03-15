from pydantic import BaseModel

class UnitBase(BaseModel):
    unit_number: str
    description: str | None = None
    rent_amount: float
    property_id: int

class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    unit_number: str | None = None
    description: str | None = None
    rent_amount: float | None = None

class UnitRead(UnitBase):
    id: int

    class Config:
        orm_mode = True
