from datetime import date

from pydantic import BaseModel, ConfigDict


class UtilityChargeBase(BaseModel):
    lease_id: int
    utility_type: str
    description: str | None = ""
    amount: float
    bill_date: date
    due_date: date | None = None


class UtilityChargeCreate(UtilityChargeBase):
    pass


class UtilityChargeUpdate(BaseModel):
    utility_type: str | None = None
    description: str | None = None
    amount: float | None = None
    bill_date: date | None = None
    due_date: date | None = None
    is_paid: bool | None = None
    paid_payment_id: int | None = None


class UtilityChargeRead(UtilityChargeBase):
    id: int
    is_paid: bool
    paid_payment_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
