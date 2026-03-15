import uuid
from sqlalchemy.orm import Session

from rental_core.models.lease import Lease, LeaseStatus
from rental_core.models.property import Property
from rental_core.models.unit import Unit
from rental_core.schemas.lease import LeaseCreate, LeaseUpdate


def list_leases(db: Session, owner_id: int):
    return (
        db.query(Lease)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Property.owner_id == owner_id)
        .all()
    )


def create_lease(db: Session, lease_in: LeaseCreate, owner_id: int):
    unit = (
        db.query(Unit)
        .join(Property, Unit.property_id == Property.id)
        .filter(Unit.id == lease_in.unit_id, Property.owner_id == owner_id)
        .first()
    )
    if not unit:
        return None

    lease = Lease(
        lease_number=str(uuid.uuid4())[:8],
        unit_id=lease_in.unit_id,
        tenant_id=lease_in.tenant_id,
        start_date=lease_in.start_date,
        end_date=lease_in.end_date,
        status=LeaseStatus.active.value,
    )
    db.add(lease)
    db.commit()
    db.refresh(lease)
    return lease


def update_lease(db: Session, lease_id: int, lease_in: LeaseUpdate, owner_id: int):
    lease = (
        db.query(Lease)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Lease.id == lease_id, Property.owner_id == owner_id)
        .first()
    )
    if not lease:
        return None

    if lease_in.status is not None:
        lease.status = lease_in.status.value if hasattr(lease_in.status, "value") else str(lease_in.status)
    if lease_in.tenant_id is not None:
        lease.tenant_id = lease_in.tenant_id
    if lease_in.end_date is not None:
        lease.end_date = lease_in.end_date

    db.commit()
    db.refresh(lease)
    return lease


def delete_lease(db: Session, lease_id: int, owner_id: int) -> bool:
    lease = (
        db.query(Lease)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Lease.id == lease_id, Property.owner_id == owner_id)
        .first()
    )
    if not lease:
        return False

    db.delete(lease)
    db.commit()
    return True
