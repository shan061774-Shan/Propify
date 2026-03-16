from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.network import (
    InviteByPhone,
    OwnerContractorLinkRead,
    OwnerTenantLinkRead,
)
from rental_core.services.network_service import (
    approve_contractor_link,
    approve_tenant_link,
    invite_contractor_by_phone,
    invite_tenant_by_phone,
    list_owner_contractor_links,
    list_owner_tenant_links,
)

router = APIRouter(prefix="/network", tags=["network"])


def _send_invite_sms(phone: str, message: str) -> None:
    try:
        from infra.send_rent_due_sms import get_twilio_client, send_sms_message

        client, from_number, messaging_service_sid = get_twilio_client()
        send_sms_message(
            client,
            phone,
            message,
            from_number=from_number,
            messaging_service_sid=messaging_service_sid,
        )
    except Exception:
        # Notification delivery is best-effort and should not block invite workflows.
        return


@router.get("/tenants", response_model=list[OwnerTenantLinkRead])
def owner_tenant_links(
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return list_owner_tenant_links(db, current_owner.id)


@router.post("/tenants/invite", response_model=OwnerTenantLinkRead)
def owner_invite_tenant(
    payload: InviteByPhone,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    link = invite_tenant_by_phone(db, current_owner.id, payload.phone)
    if not link:
        raise HTTPException(status_code=400, detail="Phone is required")
    _send_invite_sms(payload.phone, "You have been invited to connect with a property owner on Propify.")
    return link


@router.post("/tenants/{link_id}/approve", response_model=OwnerTenantLinkRead)
def owner_approve_tenant(
    link_id: int,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    link = approve_tenant_link(db, current_owner.id, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Invite not found or not eligible for approval")
    return link


@router.get("/contractors", response_model=list[OwnerContractorLinkRead])
def owner_contractor_links(
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return list_owner_contractor_links(db, current_owner.id)


@router.post("/contractors/invite", response_model=OwnerContractorLinkRead)
def owner_invite_contractor(
    payload: InviteByPhone,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    link = invite_contractor_by_phone(db, current_owner.id, payload.phone)
    if not link:
        raise HTTPException(status_code=400, detail="Phone is required")
    _send_invite_sms(payload.phone, "You have been invited to connect with a property owner on Propify.")
    return link


@router.post("/contractors/{link_id}/approve", response_model=OwnerContractorLinkRead)
def owner_approve_contractor(
    link_id: int,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    link = approve_contractor_link(db, current_owner.id, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Invite not found or not eligible for approval")
    return link
