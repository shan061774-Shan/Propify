from sqlalchemy.orm import Session

from rental_core.models.lease import Lease
from rental_core.models.property import Property
from rental_core.models.unit import Unit
from rental_core.models.utility_charge import UtilityCharge
from rental_core.schemas.utility_charge import UtilityChargeCreate, UtilityChargeUpdate


def list_utility_charges(db: Session, owner_id: int):
    return (
        db.query(UtilityCharge)
        .join(Lease, UtilityCharge.lease_id == Lease.id)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Property.owner_id == owner_id)
        .all()
    )


def list_utility_charges_by_lease(db: Session, lease_id: int, owner_id: int):
    return (
        db.query(UtilityCharge)
        .join(Lease, UtilityCharge.lease_id == Lease.id)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(UtilityCharge.lease_id == lease_id, Property.owner_id == owner_id)
        .all()
    )


def create_utility_charge(db: Session, charge_in: UtilityChargeCreate, owner_id: int):
    lease = (
        db.query(Lease)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Lease.id == charge_in.lease_id, Property.owner_id == owner_id)
        .first()
    )
    if not lease:
        return None

    charge = UtilityCharge(
        lease_id=charge_in.lease_id,
        utility_type=charge_in.utility_type,
        description=charge_in.description or "",
        amount=charge_in.amount,
        bill_date=charge_in.bill_date,
        due_date=charge_in.due_date,
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def update_utility_charge(db: Session, charge_id: int, charge_in: UtilityChargeUpdate, owner_id: int):
    charge = (
        db.query(UtilityCharge)
        .join(Lease, UtilityCharge.lease_id == Lease.id)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(UtilityCharge.id == charge_id, Property.owner_id == owner_id)
        .first()
    )
    if not charge:
        return None

    payload = charge_in.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(charge, key, value)

    db.commit()
    db.refresh(charge)
    return charge


def delete_utility_charge(db: Session, charge_id: int, owner_id: int) -> bool:
    charge = (
        db.query(UtilityCharge)
        .join(Lease, UtilityCharge.lease_id == Lease.id)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(UtilityCharge.id == charge_id, Property.owner_id == owner_id)
        .first()
    )
    if not charge:
        return False

    db.delete(charge)
    db.commit()
    return True
