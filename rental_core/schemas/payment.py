# rental_core/schemas/payment.py
from datetime import date
from pydantic import BaseModel

class PaymentCreate(BaseModel):
    lease_id: int
    amount: float
    date: date

class PaymentRead(PaymentCreate):
    id: int

    class Config:
        from_attributes = True