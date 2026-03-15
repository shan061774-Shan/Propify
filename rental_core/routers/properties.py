from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.property import PropertyCreate, PropertyRead, PropertyUpdate
from rental_core.services.property_service import (
    list_properties,
    create_property,
    delete_property,
    update_property,
)

router = APIRouter(prefix="/properties", tags=["properties"])

@router.get("/", response_model=list[PropertyRead])
def get_properties(db: Session = Depends(get_db), current_owner: OwnerAccount = Depends(get_current_owner)):
    return list_properties(db, current_owner.id)

@router.post("/", response_model=PropertyRead)
def create_property_route(
    property_in: PropertyCreate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    return create_property(db, property_in, current_owner.id)

@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property_route(
    property_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    if not delete_property(db, property_id, current_owner.id):
        raise HTTPException(status_code=404, detail="Property not found")


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property_route(
    property_id: int,
    property_in: PropertyUpdate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    updated = update_property(db, property_id, property_in, current_owner.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Property not found")
    return updated
