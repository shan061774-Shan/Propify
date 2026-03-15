from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.contractor import ContractorCreate, ContractorRead, ContractorUpdate
from rental_core.services.contractor_service import (
    create_contractor,
    delete_contractor,
    get_contractor,
    list_contractors,
    update_contractor,
)

router = APIRouter(prefix="/contractors", tags=["contractors"])


@router.get("/", response_model=list[ContractorRead])
def get_contractors(
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return list_contractors(db, current_owner.id)


@router.get("/{contractor_id}", response_model=ContractorRead)
def get_contractor_route(
    contractor_id: int,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    c = get_contractor(db, current_owner.id, contractor_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contractor not found")
    return c


@router.post("/", response_model=ContractorRead)
def create_contractor_route(
    contractor_in: ContractorCreate,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return create_contractor(db, current_owner.id, contractor_in)


@router.patch("/{contractor_id}", response_model=ContractorRead)
def update_contractor_route(
    contractor_id: int,
    contractor_in: ContractorUpdate,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    c = update_contractor(db, current_owner.id, contractor_id, contractor_in)
    if not c:
        raise HTTPException(status_code=404, detail="Contractor not found")
    return c


@router.delete("/{contractor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contractor_route(
    contractor_id: int,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    if not delete_contractor(db, current_owner.id, contractor_id):
        raise HTTPException(status_code=404, detail="Contractor not found")
