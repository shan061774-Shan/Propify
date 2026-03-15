from sqlalchemy.orm import Session
from rental_core.models.maintenance import MaintenanceRequest
from rental_core.models.property import Property
from rental_core.models.unit import Unit
from rental_core.schemas.maintenance import MaintenanceCreate, MaintenanceUpdate

def list_requests(db: Session, owner_id: int):
    return (
        db.query(MaintenanceRequest)
        .join(Unit, MaintenanceRequest.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Property.owner_id == owner_id)
        .all()
    )

def create_request(db: Session, req_in: MaintenanceCreate, owner_id: int):
    from datetime import date as _date
    unit = (
        db.query(Unit)
        .join(Property, Unit.property_id == Property.id)
        .filter(Unit.id == req_in.unit_id, Property.owner_id == owner_id)
        .first()
    )
    if not unit:
        return None

    req = MaintenanceRequest(
        unit_id=req_in.unit_id,
        description=req_in.description,
        priority=req_in.priority,
        status=req_in.status.value if hasattr(req_in.status, "value") else str(req_in.status),
        contractor_id=req_in.contractor_id,
        photo_path=req_in.photo_path,
        request_date=req_in.request_date or _date.today(),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req

def delete_request(db: Session, request_id: int, owner_id: int) -> bool:
    req = (
        db.query(MaintenanceRequest)
        .join(Unit, MaintenanceRequest.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(MaintenanceRequest.id == request_id, Property.owner_id == owner_id)
        .first()
    )
    if not req:
        return False
    db.delete(req)
    db.commit()
    return True

def update_request(db: Session, request_id: int, req_in: MaintenanceUpdate, owner_id: int):
    req = (
        db.query(MaintenanceRequest)
        .join(Unit, MaintenanceRequest.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(MaintenanceRequest.id == request_id, Property.owner_id == owner_id)
        .first()
    )
    if not req:
        return None

    for field, value in req_in.model_dump(exclude_unset=True).items():
        if field == "status" and value is not None:
            setattr(req, field, value.value if hasattr(value, "value") else str(value))
        else:
            setattr(req, field, value)

    db.commit()
    db.refresh(req)
    return req
