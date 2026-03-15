from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.tenant import TenantCreate, TenantRead, TenantUpdate
from rental_core.services.tenant_service import list_tenants, create_tenant, update_tenant, delete_tenant

router = APIRouter(prefix="/tenants", tags=["tenants"])

@router.get("/", response_model=list[TenantRead])
def get_tenants(
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return list_tenants(db, current_owner.id)

@router.post("/", response_model=TenantRead)
def create_tenant_route(
    tenant_in: TenantCreate,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return create_tenant(db, current_owner.id, tenant_in)

@router.patch("/{tenant_id}", response_model=TenantRead)
def update_tenant_route(
    tenant_id: int,
    tenant_in: TenantUpdate,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    t = update_tenant(db, current_owner.id, tenant_id, tenant_in)
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return t

@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant_route(
    tenant_id: int,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    if not delete_tenant(db, current_owner.id, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
