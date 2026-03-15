from datetime import datetime

from sqlalchemy.orm import Session

from rental_core.models.contractor import Contractor
from rental_core.models.owner_contractor_link import OwnerContractorLink
from rental_core.schemas.contractor import ContractorCreate, ContractorUpdate
from rental_core.services.network_service import list_owner_contractors


def _normalize_phone(phone: str | None) -> str:
    return (phone or "").strip()


def _find_owner_contractor_link(db: Session, owner_id: int, contractor: Contractor):
    if contractor.phone:
        link = (
            db.query(OwnerContractorLink)
            .filter(OwnerContractorLink.owner_id == owner_id, OwnerContractorLink.phone == contractor.phone)
            .first()
        )
        if link:
            return link
    return (
        db.query(OwnerContractorLink)
        .filter(OwnerContractorLink.owner_id == owner_id, OwnerContractorLink.contractor_id == contractor.id)
        .first()
    )


def _upsert_owner_contractor_link(db: Session, owner_id: int, contractor: Contractor):
    if not contractor.phone:
        return
    link = _find_owner_contractor_link(db, owner_id, contractor)
    now = datetime.utcnow()
    if not link:
        link = OwnerContractorLink(
            owner_id=owner_id,
            contractor_id=contractor.id,
            phone=contractor.phone,
            status="approved",
            accepted_at=now,
            approved_at=now,
        )
        db.add(link)
        return

    link.phone = contractor.phone
    link.contractor_id = contractor.id
    link.status = "approved"
    if not link.accepted_at:
        link.accepted_at = now
    link.approved_at = now


def list_contractors(db: Session, owner_id: int):
    return list_owner_contractors(db, owner_id)


def get_contractor(db: Session, owner_id: int, contractor_id: int):
    return (
        db.query(Contractor)
        .join(OwnerContractorLink, OwnerContractorLink.contractor_id == Contractor.id)
        .filter(
            Contractor.id == contractor_id,
            OwnerContractorLink.owner_id == owner_id,
            OwnerContractorLink.status == "approved",
        )
        .first()
    )


def create_contractor(db: Session, owner_id: int, contractor_in: ContractorCreate):
    normalized_phone = _normalize_phone(contractor_in.phone)
    existing = db.query(Contractor).filter(Contractor.phone == normalized_phone).first() if normalized_phone else None
    if existing:
        for field, value in contractor_in.model_dump().items():
            if value is not None:
                setattr(existing, field, value.strip() if isinstance(value, str) else value)
        _upsert_owner_contractor_link(db, owner_id, existing)
        db.commit()
        db.refresh(existing)
        return existing

    payload = contractor_in.model_dump()
    payload["phone"] = normalized_phone
    payload = {k: (v.strip() if isinstance(v, str) else v) for k, v in payload.items()}
    contractor = Contractor(**payload)
    db.add(contractor)
    db.flush()
    _upsert_owner_contractor_link(db, owner_id, contractor)
    db.commit()
    db.refresh(contractor)
    return contractor


def update_contractor(db: Session, owner_id: int, contractor_id: int, contractor_in: ContractorUpdate):
    contractor = get_contractor(db, owner_id, contractor_id)
    if not contractor:
        return None
    for field, value in contractor_in.model_dump(exclude_unset=True).items():
        if field == "phone":
            setattr(contractor, field, _normalize_phone(value))
        elif isinstance(value, str):
            setattr(contractor, field, value.strip())
        else:
            setattr(contractor, field, value)

    _upsert_owner_contractor_link(db, owner_id, contractor)
    db.commit()
    db.refresh(contractor)
    return contractor


def delete_contractor(db: Session, owner_id: int, contractor_id: int) -> bool:
    link = (
        db.query(OwnerContractorLink)
        .filter(
            OwnerContractorLink.owner_id == owner_id,
            OwnerContractorLink.contractor_id == contractor_id,
            OwnerContractorLink.status == "approved",
        )
        .first()
    )
    if not link:
        return False

    db.delete(link)
    db.commit()
    return True
