from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.payment import PaymentCreate, PaymentRead
from rental_core.services.payment_service import list_payments, create_payment, delete_payment

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/", response_model=list[PaymentRead])
def get_payments(db: Session = Depends(get_db), current_owner: OwnerAccount = Depends(get_current_owner)):
    return list_payments(db, current_owner.id)


@router.post("/", response_model=PaymentRead)
def create_payment_route(
    payment_in: PaymentCreate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    payment = create_payment(db, payment_in, current_owner.id)
    if not payment:
        raise HTTPException(status_code=404, detail="Lease not found")
    return payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_route(
    payment_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    if not delete_payment(db, payment_id, current_owner.id):
        raise HTTPException(status_code=404, detail="Payment not found")
