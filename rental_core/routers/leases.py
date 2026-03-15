from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.lease import LeaseCreate, LeaseRead, LeaseUpdate
from rental_core.services.lease_service import list_leases, create_lease, update_lease, delete_lease

router = APIRouter(prefix="/leases", tags=["leases"])


@router.get("/", response_model=list[LeaseRead])
def get_leases(db: Session = Depends(get_db), current_owner: OwnerAccount = Depends(get_current_owner)):
    return list_leases(db, current_owner.id)


@router.post("/", response_model=LeaseRead)
def create_lease_route(
    lease_in: LeaseCreate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    lease = create_lease(db, lease_in, current_owner.id)
    if not lease:
        raise HTTPException(status_code=404, detail="Unit not found")
    return lease


@router.patch("/{lease_id}", response_model=LeaseRead)
def update_lease_route(
    lease_id: int,
    lease_in: LeaseUpdate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    lease = update_lease(db, lease_id, lease_in, current_owner.id)
    if not lease:
        raise HTTPException(status_code=404, detail="Lease not found")
    return lease


@router.delete("/{lease_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lease_route(
    lease_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    if not delete_lease(db, lease_id, current_owner.id):
        raise HTTPException(status_code=404, detail="Lease not found")
