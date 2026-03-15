from datetime import date

from sqlalchemy.orm import Session

from rental_core.models.document import Document
from rental_core.models.lease import Lease
from rental_core.models.maintenance import MaintenanceRequest
from rental_core.models.property import Property
from rental_core.models.unit import Unit
from rental_core.services.document_service import get_document, list_documents_by_tenant


def tenant_active_lease_rows(db: Session, tenant_id: int) -> list[tuple[Lease, Unit, Property]]:
    return (
        db.query(Lease, Unit, Property)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Lease.tenant_id == tenant_id, Lease.status == "active")
        .all()
    )


def tenant_allowed_lease_ids(db: Session, tenant_id: int) -> set[int]:
    return {lease.id for lease, _, _ in tenant_active_lease_rows(db, tenant_id)}


def tenant_request_rows(db: Session, tenant_id: int) -> list[tuple[MaintenanceRequest, Unit, Property]]:
    rows = tenant_active_lease_rows(db, tenant_id)
    unit_map = {unit.id: (unit, prop) for _, unit, prop in rows}
    if not unit_map:
        return []

    requests = (
        db.query(MaintenanceRequest)
        .filter(MaintenanceRequest.unit_id.in_(list(unit_map.keys())))
        .order_by(MaintenanceRequest.request_date.desc(), MaintenanceRequest.id.desc())
        .all()
    )
    return [(req, *unit_map[req.unit_id]) for req in requests if req.unit_id in unit_map]


def create_tenant_request_scoped(
    db: Session,
    tenant_id: int,
    unit_id: int,
    description: str,
    priority: str,
    photo_path: str | None,
) -> tuple[MaintenanceRequest, Unit, Property] | None:
    rows = tenant_active_lease_rows(db, tenant_id)
    unit_map = {unit.id: (unit, prop) for _, unit, prop in rows}
    if unit_id not in unit_map:
        return None

    req = MaintenanceRequest(
        unit_id=unit_id,
        description=description,
        priority=priority,
        status="pending",
        photo_path=photo_path,
        request_date=date.today(),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    unit, prop = unit_map[unit_id]
    return req, unit, prop


def list_tenant_documents_scoped(db: Session, tenant_id: int):
    return list_documents_by_tenant(db, tenant_id)


def get_tenant_document_scoped(db: Session, tenant_id: int, document_id: int) -> Document | None:
    doc = get_document(db, document_id)
    if not doc or doc.tenant_id != tenant_id:
        return None
    return doc


def contractor_request_rows(db: Session, contractor_id: int) -> list[tuple[MaintenanceRequest, Unit, Property]]:
    return (
        db.query(MaintenanceRequest, Unit, Property)
        .join(Unit, MaintenanceRequest.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(MaintenanceRequest.contractor_id == contractor_id)
        .order_by(MaintenanceRequest.request_date.desc(), MaintenanceRequest.id.desc())
        .all()
    )


def update_contractor_request_status_scoped(
    db: Session,
    contractor_id: int,
    request_id: int,
    status_value: str,
) -> tuple[MaintenanceRequest, Unit, Property] | None:
    req = (
        db.query(MaintenanceRequest)
        .filter(MaintenanceRequest.id == request_id, MaintenanceRequest.contractor_id == contractor_id)
        .first()
    )
    if not req:
        return None

    req.status = status_value
    req.closed_date = date.today() if status_value == "closed" else None
    db.commit()
    db.refresh(req)

    unit = db.query(Unit).filter(Unit.id == req.unit_id).first()
    if not unit:
        return None
    prop = db.query(Property).filter(Property.id == unit.property_id).first()
    if not prop:
        return None
    return req, unit, prop
