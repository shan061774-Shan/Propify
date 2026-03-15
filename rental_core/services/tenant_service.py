from datetime import datetime

from sqlalchemy.orm import Session

from rental_core.models.owner_tenant_link import OwnerTenantLink
from rental_core.models.tenant import Tenant
from rental_core.schemas.tenant import TenantCreate, TenantUpdate
from rental_core.services.network_service import list_owner_tenants


def _normalize_phone(phone: str | None) -> str:
    return (phone or "").strip()


def _find_owner_tenant_link(db: Session, owner_id: int, tenant: Tenant):
    if tenant.phone:
        link = (
            db.query(OwnerTenantLink)
            .filter(OwnerTenantLink.owner_id == owner_id, OwnerTenantLink.phone == tenant.phone)
            .first()
        )
        if link:
            return link
    return (
        db.query(OwnerTenantLink)
        .filter(OwnerTenantLink.owner_id == owner_id, OwnerTenantLink.tenant_id == tenant.id)
        .first()
    )


def _upsert_owner_tenant_link(db: Session, owner_id: int, tenant: Tenant):
    if not tenant.phone:
        return
    link = _find_owner_tenant_link(db, owner_id, tenant)
    now = datetime.utcnow()
    if not link:
        link = OwnerTenantLink(
            owner_id=owner_id,
            tenant_id=tenant.id,
            phone=tenant.phone,
            status="approved",
            accepted_at=now,
            approved_at=now,
        )
        db.add(link)
        return

    link.phone = tenant.phone
    link.tenant_id = tenant.id
    link.status = "approved"
    if not link.accepted_at:
        link.accepted_at = now
    link.approved_at = now


def list_tenants(db: Session, owner_id: int):
    return list_owner_tenants(db, owner_id)


def create_tenant(db: Session, owner_id: int, tenant_in: TenantCreate):
    normalized_phone = _normalize_phone(tenant_in.phone)
    existing = db.query(Tenant).filter(Tenant.phone == normalized_phone).first() if normalized_phone else None
    if existing:
        if tenant_in.name and tenant_in.name.strip():
            existing.name = tenant_in.name.strip()
        if tenant_in.email is not None:
            existing.email = tenant_in.email.strip()
        _upsert_owner_tenant_link(db, owner_id, existing)
        db.commit()
        db.refresh(existing)
        return existing

    tenant = Tenant(
        name=tenant_in.name.strip(),
        email=(tenant_in.email or "").strip(),
        phone=normalized_phone,
    )
    db.add(tenant)
    db.flush()
    _upsert_owner_tenant_link(db, owner_id, tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def update_tenant(db: Session, owner_id: int, tenant_id: int, tenant_in: TenantUpdate):
    tenant = (
        db.query(Tenant)
        .join(OwnerTenantLink, OwnerTenantLink.tenant_id == Tenant.id)
        .filter(
            Tenant.id == tenant_id,
            OwnerTenantLink.owner_id == owner_id,
            OwnerTenantLink.status == "approved",
        )
        .first()
    )
    if not tenant:
        return None
    for field, value in tenant_in.model_dump(exclude_unset=True).items():
        if field == "phone":
            setattr(tenant, field, _normalize_phone(value))
        elif isinstance(value, str):
            setattr(tenant, field, value.strip())
        else:
            setattr(tenant, field, value)

    _upsert_owner_tenant_link(db, owner_id, tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def delete_tenant(db: Session, owner_id: int, tenant_id: int) -> bool:
    link = (
        db.query(OwnerTenantLink)
        .filter(
            OwnerTenantLink.owner_id == owner_id,
            OwnerTenantLink.tenant_id == tenant_id,
            OwnerTenantLink.status == "approved",
        )
        .first()
    )
    if not link:
        return False

    db.delete(link)
    db.commit()
    return True
