from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.utility_charge import UtilityChargeCreate, UtilityChargeRead, UtilityChargeUpdate
from rental_core.services.utility_charge_service import (
    create_utility_charge,
    delete_utility_charge,
    list_utility_charges,
    list_utility_charges_by_lease,
    update_utility_charge,
)


router = APIRouter(prefix="/utility-charges", tags=["utility-charges"])


@router.get("/", response_model=list[UtilityChargeRead])
def get_utility_charges(db: Session = Depends(get_db), current_owner: OwnerAccount = Depends(get_current_owner)):
    return list_utility_charges(db, current_owner.id)


@router.get("/lease/{lease_id}", response_model=list[UtilityChargeRead])
def get_utility_charges_by_lease(
    lease_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    return list_utility_charges_by_lease(db, lease_id, current_owner.id)


@router.post("/", response_model=UtilityChargeRead)
def create_utility_charge_route(
    charge_in: UtilityChargeCreate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    created = create_utility_charge(db, charge_in, current_owner.id)
    if not created:
        raise HTTPException(status_code=404, detail="Lease not found")
    return created


@router.patch("/{charge_id}", response_model=UtilityChargeRead)
def update_utility_charge_route(
    charge_id: int,
    charge_in: UtilityChargeUpdate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    updated = update_utility_charge(db, charge_id, charge_in, current_owner.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Utility charge not found")
    return updated


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_utility_charge_route(
    charge_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    if not delete_utility_charge(db, charge_id, current_owner.id):
        raise HTTPException(status_code=404, detail="Utility charge not found")
