from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.unit import UnitCreate, UnitRead, UnitUpdate
from rental_core.services.unit_service import list_units, create_unit, delete_unit, update_unit

router = APIRouter(prefix="/units", tags=["units"])

@router.get("/", response_model=list[UnitRead])
def get_units(db: Session = Depends(get_db), current_owner: OwnerAccount = Depends(get_current_owner)):
    return list_units(db, current_owner.id)

@router.post("/", response_model=UnitRead)
def create_unit_route(
    unit_in: UnitCreate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    created = create_unit(db, unit_in, current_owner.id)
    if not created:
        raise HTTPException(status_code=404, detail="Property not found")
    return created

@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit_route(
    unit_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    if not delete_unit(db, unit_id, current_owner.id):
        raise HTTPException(status_code=404, detail="Unit not found")


@router.patch("/{unit_id}", response_model=UnitRead)
def update_unit_route(
    unit_id: int,
    unit_in: UnitUpdate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    updated = update_unit(db, unit_id, unit_in, current_owner.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Unit not found")
    return updated