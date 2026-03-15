from sqlalchemy.orm import Session
from rental_core.models.property import Property
from rental_core.models.unit import Unit
from rental_core.schemas.unit import UnitCreate, UnitUpdate

def list_units(db: Session, owner_id: int):
    return (
        db.query(Unit)
        .join(Property, Unit.property_id == Property.id)
        .filter(Property.owner_id == owner_id)
        .all()
    )

def create_unit(db: Session, unit_in: UnitCreate, owner_id: int):
    prop = db.query(Property).filter(Property.id == unit_in.property_id, Property.owner_id == owner_id).first()
    if not prop:
        return None

    db_unit = Unit(
        unit_number=unit_in.unit_number,
        description=unit_in.description,
        rent_amount=unit_in.rent_amount,
        property_id=unit_in.property_id,
    )
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

def delete_unit(db: Session, unit_id: int, owner_id: int) -> bool:
    unit = (
        db.query(Unit)
        .join(Property, Unit.property_id == Property.id)
        .filter(Unit.id == unit_id, Property.owner_id == owner_id)
        .first()
    )
    if not unit:
        return False
    db.delete(unit)
    db.commit()
    return True


def update_unit(db: Session, unit_id: int, unit_in: UnitUpdate, owner_id: int):
    unit = (
        db.query(Unit)
        .join(Property, Unit.property_id == Property.id)
        .filter(Unit.id == unit_id, Property.owner_id == owner_id)
        .first()
    )
    if not unit:
        return None

    payload = unit_in.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(unit, key, value)

    db.commit()
    db.refresh(unit)
    return unit
