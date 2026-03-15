from datetime import datetime

from sqlalchemy.orm import Session

from rental_core.models.contractor import Contractor
from rental_core.models.owner_contractor_link import OwnerContractorLink
from rental_core.models.owner_tenant_link import OwnerTenantLink
from rental_core.models.tenant import Tenant


def _normalize_phone(phone: str) -> str:
    return (phone or "").strip()


def invite_tenant_by_phone(db: Session, owner_id: int, phone: str):
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return None

    tenant = db.query(Tenant).filter(Tenant.phone == normalized_phone).first()
    link = (
        db.query(OwnerTenantLink)
        .filter(OwnerTenantLink.owner_id == owner_id, OwnerTenantLink.phone == normalized_phone)
        .first()
    )
    if link:
        link.status = "invited"
        link.tenant_id = tenant.id if tenant else link.tenant_id
        link.invited_at = datetime.utcnow()
        link.accepted_at = None
        link.approved_at = None
    else:
        link = OwnerTenantLink(
            owner_id=owner_id,
            tenant_id=tenant.id if tenant else None,
            phone=normalized_phone,
            status="invited",
        )
        db.add(link)

    db.commit()
    db.refresh(link)
    return link


def invite_contractor_by_phone(db: Session, owner_id: int, phone: str):
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return None

    contractor = db.query(Contractor).filter(Contractor.phone == normalized_phone).first()
    link = (
        db.query(OwnerContractorLink)
        .filter(OwnerContractorLink.owner_id == owner_id, OwnerContractorLink.phone == normalized_phone)
        .first()
    )
    if link:
        link.status = "invited"
        link.contractor_id = contractor.id if contractor else link.contractor_id
        link.invited_at = datetime.utcnow()
        link.accepted_at = None
        link.approved_at = None
    else:
        link = OwnerContractorLink(
            owner_id=owner_id,
            contractor_id=contractor.id if contractor else None,
            phone=normalized_phone,
            status="invited",
        )
        db.add(link)

    db.commit()
    db.refresh(link)
    return link


def list_owner_tenant_links(db: Session, owner_id: int):
    return (
        db.query(OwnerTenantLink)
        .filter(OwnerTenantLink.owner_id == owner_id)
        .order_by(OwnerTenantLink.invited_at.desc(), OwnerTenantLink.id.desc())
        .all()
    )


def list_owner_contractor_links(db: Session, owner_id: int):
    return (
        db.query(OwnerContractorLink)
        .filter(OwnerContractorLink.owner_id == owner_id)
        .order_by(OwnerContractorLink.invited_at.desc(), OwnerContractorLink.id.desc())
        .all()
    )


def approve_tenant_link(db: Session, owner_id: int, link_id: int):
    link = (
        db.query(OwnerTenantLink)
        .filter(OwnerTenantLink.id == link_id, OwnerTenantLink.owner_id == owner_id)
        .first()
    )
    if not link or link.status != "accepted":
        return None

    link.status = "approved"
    link.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(link)
    return link


def approve_contractor_link(db: Session, owner_id: int, link_id: int):
    link = (
        db.query(OwnerContractorLink)
        .filter(OwnerContractorLink.id == link_id, OwnerContractorLink.owner_id == owner_id)
        .first()
    )
    if not link or link.status != "accepted":
        return None

    link.status = "approved"
    link.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(link)
    return link


def link_tenant_to_phone_invites(db: Session, tenant: Tenant):
    normalized_phone = _normalize_phone(tenant.phone or "")
    if not normalized_phone:
        return

    links = (
        db.query(OwnerTenantLink)
        .filter(OwnerTenantLink.phone == normalized_phone, OwnerTenantLink.tenant_id.is_(None))
        .all()
    )
    for link in links:
        link.tenant_id = tenant.id
    if links:
        db.commit()


def link_contractor_to_phone_invites(db: Session, contractor: Contractor):
    normalized_phone = _normalize_phone(contractor.phone or "")
    if not normalized_phone:
        return

    links = (
        db.query(OwnerContractorLink)
        .filter(OwnerContractorLink.phone == normalized_phone, OwnerContractorLink.contractor_id.is_(None))
        .all()
    )
    for link in links:
        link.contractor_id = contractor.id
    if links:
        db.commit()


def list_tenant_invites(db: Session, tenant_id: int):
    return (
        db.query(OwnerTenantLink)
        .filter(OwnerTenantLink.tenant_id == tenant_id)
        .order_by(OwnerTenantLink.invited_at.desc(), OwnerTenantLink.id.desc())
        .all()
    )


def list_tenant_invites_by_phone(db: Session, phone: str):
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return []
    return (
        db.query(OwnerTenantLink)
        .filter(OwnerTenantLink.phone == normalized_phone)
        .order_by(OwnerTenantLink.invited_at.desc(), OwnerTenantLink.id.desc())
        .all()
    )


def list_contractor_invites(db: Session, contractor_id: int):
    return (
        db.query(OwnerContractorLink)
        .filter(OwnerContractorLink.contractor_id == contractor_id)
        .order_by(OwnerContractorLink.invited_at.desc(), OwnerContractorLink.id.desc())
        .all()
    )


def list_contractor_invites_by_phone(db: Session, phone: str):
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return []
    return (
        db.query(OwnerContractorLink)
        .filter(OwnerContractorLink.phone == normalized_phone)
        .order_by(OwnerContractorLink.invited_at.desc(), OwnerContractorLink.id.desc())
        .all()
    )


def accept_tenant_invite(db: Session, tenant_id: int, link_id: int):
    link = (
        db.query(OwnerTenantLink)
        .filter(OwnerTenantLink.id == link_id, OwnerTenantLink.tenant_id == tenant_id)
        .first()
    )
    if not link or link.status not in {"invited", "accepted"}:
        return None

    link.status = "accepted"
    link.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(link)
    return link


def accept_tenant_invite_by_phone(
    db: Session,
    link_id: int,
    phone: str,
    name: str,
    email: str | None = None,
):
    normalized_phone = _normalize_phone(phone)
    link = (
        db.query(OwnerTenantLink)
        .filter(OwnerTenantLink.id == link_id, OwnerTenantLink.phone == normalized_phone)
        .first()
    )
    if not link or link.status not in {"invited", "accepted"}:
        return None

    tenant = db.query(Tenant).filter(Tenant.phone == normalized_phone).first()
    if not tenant:
        tenant = Tenant(name=name.strip(), email=(email or "").strip(), phone=normalized_phone)
        db.add(tenant)
        db.flush()
    else:
        if name and name.strip():
            tenant.name = name.strip()
        if email is not None:
            tenant.email = email.strip()

    link.tenant_id = tenant.id
    link.status = "accepted"
    link.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(link)
    return link


def accept_contractor_invite(db: Session, contractor_id: int, link_id: int):
    link = (
        db.query(OwnerContractorLink)
        .filter(OwnerContractorLink.id == link_id, OwnerContractorLink.contractor_id == contractor_id)
        .first()
    )
    if not link or link.status not in {"invited", "accepted"}:
        return None

    link.status = "accepted"
    link.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(link)
    return link


def accept_contractor_invite_by_phone(
    db: Session,
    link_id: int,
    phone: str,
    name: str,
    email: str | None = None,
    specialty: str | None = None,
):
    normalized_phone = _normalize_phone(phone)
    link = (
        db.query(OwnerContractorLink)
        .filter(OwnerContractorLink.id == link_id, OwnerContractorLink.phone == normalized_phone)
        .first()
    )
    if not link or link.status not in {"invited", "accepted"}:
        return None

    contractor = db.query(Contractor).filter(Contractor.phone == normalized_phone).first()
    if not contractor:
        contractor = Contractor(
            name=name.strip(),
            email=(email or "").strip(),
            phone=normalized_phone,
            specialty=(specialty or "").strip(),
        )
        db.add(contractor)
        db.flush()
    else:
        if name and name.strip():
            contractor.name = name.strip()
        if email is not None:
            contractor.email = email.strip()
        if specialty is not None:
            contractor.specialty = specialty.strip()

    link.contractor_id = contractor.id
    link.status = "accepted"
    link.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(link)
    return link


def owner_has_tenant(db: Session, owner_id: int, tenant_id: int) -> bool:
    link = (
        db.query(OwnerTenantLink)
        .filter(
            OwnerTenantLink.owner_id == owner_id,
            OwnerTenantLink.tenant_id == tenant_id,
            OwnerTenantLink.status == "approved",
        )
        .first()
    )
    return bool(link)


def owner_has_contractor(db: Session, owner_id: int, contractor_id: int) -> bool:
    link = (
        db.query(OwnerContractorLink)
        .filter(
            OwnerContractorLink.owner_id == owner_id,
            OwnerContractorLink.contractor_id == contractor_id,
            OwnerContractorLink.status == "approved",
        )
        .first()
    )
    return bool(link)


def list_owner_tenants(db: Session, owner_id: int):
    return (
        db.query(Tenant)
        .join(OwnerTenantLink, OwnerTenantLink.tenant_id == Tenant.id)
        .filter(OwnerTenantLink.owner_id == owner_id, OwnerTenantLink.status == "approved")
        .order_by(Tenant.name.asc())
        .all()
    )


def list_owner_contractors(db: Session, owner_id: int):
    return (
        db.query(Contractor)
        .join(OwnerContractorLink, OwnerContractorLink.contractor_id == Contractor.id)
        .filter(OwnerContractorLink.owner_id == owner_id, OwnerContractorLink.status == "approved")
        .order_by(Contractor.name.asc())
        .all()
    )
