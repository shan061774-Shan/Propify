from sqlalchemy.orm import Session
from rental_core.models.property import Property
from rental_core.schemas.property import PropertyCreate, PropertyUpdate

def list_properties(db: Session, owner_id: int):
    return db.query(Property).filter(Property.owner_id == owner_id).all()

def create_property(db: Session, property_in: PropertyCreate, owner_id: int):
    prop = Property(
        name=property_in.name,
        address=property_in.address,
        grace_period_days=property_in.grace_period_days,
        late_fee_amount=property_in.late_fee_amount,
        owner_id=owner_id,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop

def delete_property(db: Session, property_id: int, owner_id: int) -> bool:
    prop = db.query(Property).filter(Property.id == property_id, Property.owner_id == owner_id).first()
    if not prop:
        return False
    db.delete(prop)
    db.commit()
    return True


def update_property(db: Session, property_id: int, property_in: PropertyUpdate, owner_id: int):
    prop = db.query(Property).filter(Property.id == property_id, Property.owner_id == owner_id).first()
    if not prop:
        return None

    payload = property_in.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(prop, key, value)

    db.commit()
    db.refresh(prop)
    return prop

