from sqlalchemy.orm import Session
from rental_core.models.lease import Lease
from rental_core.models.payment import Payment
from rental_core.models.property import Property
from rental_core.models.unit import Unit
from rental_core.models.utility_charge import UtilityCharge
from rental_core.schemas.payment import PaymentCreate


def list_payments(db: Session, owner_id: int):
    return (
        db.query(Payment)
        .join(Lease, Payment.lease_id == Lease.id)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Property.owner_id == owner_id)
        .all()
    )


def create_payment(db: Session, payment_in: PaymentCreate, owner_id: int):
    lease = (
        db.query(Lease)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Lease.id == payment_in.lease_id, Property.owner_id == owner_id)
        .first()
    )
    if not lease:
        return None

    payment = Payment(
        lease_id=payment_in.lease_id,
        amount=payment_in.amount,
        date=payment_in.date,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def delete_payment(db: Session, payment_id: int, owner_id: int) -> bool:
    payment = (
        db.query(Payment)
        .join(Lease, Payment.lease_id == Lease.id)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Payment.id == payment_id, Property.owner_id == owner_id)
        .first()
    )
    if not payment:
        return False

    # Reopen utility charges that were settled by this payment.
    linked_charges = (
        db.query(UtilityCharge)
        .filter(UtilityCharge.paid_payment_id == payment_id)
        .all()
    )
    for charge in linked_charges:
        charge.is_paid = False
        charge.paid_payment_id = None

    db.delete(payment)
    db.commit()
    return True
