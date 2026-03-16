import os
import hmac

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from rental_core.auth import (
    create_owner_access_token,
    create_owner_admin_access_token,
    create_propify_admin_access_token,
    get_current_owner,
    get_current_propify_admin,
)
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.owner import (
    OwnerBlockByPhoneRequest,
    OwnerAdminAcceptInviteRequest,
    OwnerAdminInviteRequest,
    OwnerAdminRead,
    OwnerLogin,
    OwnerLoginResponse,
    OwnerOperationResponse,
    OwnerOpsLoginRequest,
    OwnerOpsLoginResponse,
    OwnerTwilioStatusResponse,
    OwnerPasswordResetConfirm,
    OwnerPasswordResetConfirmResponse,
    OwnerPasswordResetRequest,
    OwnerPasswordResetRequestResponse,
    OwnerRegisterPhoneRequest,
    OwnerRegisterPhoneResponse,
    OwnerRead,
    OwnerSetup,
    OwnerStatus,
    OwnerStatusByPhoneRequest,
    OwnerStatusByPhoneResponse,
    OwnerUpdate,
)
from rental_core.services.owner_service import (
    block_owner_by_phone,
    confirm_owner_password_reset,
    create_owner,
    get_owner,
    get_owner_status_by_phone,
    invite_owner_admin,
    list_owner_admins,
    lookup_owner_admin_invites,
    login_owner,
    normalize_owner_phone,
    register_owner_phone,
    accept_owner_admin_invite,
    request_owner_password_reset,
    unblock_owner_by_phone,
    update_owner,
)

router = APIRouter(prefix="/owner", tags=["owner"])
EXPOSE_RESET_TOKEN = os.getenv("PROPIFY_EXPOSE_RESET_TOKEN", "1").strip().lower() in {"1", "true", "yes", "on"}
MASTER_ADMIN_USER = os.getenv("PROPIFY_MASTER_ADMIN_USER", "shan061774").strip()
MASTER_ADMIN_PASSWORD = os.getenv("PROPIFY_MASTER_ADMIN_PASSWORD", "shan061774").strip()


def _twilio_status() -> tuple[bool, str]:
    has_sid = bool((os.getenv("TWILIO_ACCOUNT_SID") or "").strip())
    has_token = bool((os.getenv("TWILIO_AUTH_TOKEN") or "").strip())
    has_msg_service = bool((os.getenv("TWILIO_MESSAGING_SERVICE_SID") or "").strip())
    has_from_number = bool((os.getenv("TWILIO_FROM_NUMBER") or os.getenv("TWILIO_FROM_PHONE") or "").strip())

    configured = has_sid and has_token and (has_msg_service or has_from_number)
    sender_mode = "messaging_service" if has_msg_service else ("from_number" if has_from_number else "missing")
    return configured, sender_mode


def _send_owner_admin_invite_sms(phone: str) -> None:
    try:
        from infra.send_rent_due_sms import get_twilio_client, send_sms_message

        client, from_number, messaging_service_sid = get_twilio_client()
        message = (
            "You have been invited to help manage a company in Propify. "
            "Open the Home page, use Accept Company Admin Invite, and finish your setup with this phone number."
        )
        send_sms_message(
            client,
            phone,
            message,
            from_number=from_number,
            messaging_service_sid=messaging_service_sid,
        )
    except Exception:
        return


def _verify_master_admin_login(username: str, password: str) -> bool:
    if not MASTER_ADMIN_USER or not MASTER_ADMIN_PASSWORD:
        return False
    return hmac.compare_digest((username or "").strip(), MASTER_ADMIN_USER) and hmac.compare_digest(
        password or "", MASTER_ADMIN_PASSWORD
    )


@router.get("/profile", response_model=OwnerRead)
def get_owner_profile(current_owner: OwnerAccount = Depends(get_current_owner)):
    return current_owner


@router.get("/status", response_model=OwnerStatus)
def get_owner_status(db: Session = Depends(get_db)):
    return OwnerStatus(is_setup=bool(get_owner(db)))


@router.get("/twilio-status", response_model=OwnerTwilioStatusResponse)
def get_twilio_status(current_owner: OwnerAccount = Depends(get_current_owner)):
    configured, sender_mode = _twilio_status()
    return OwnerTwilioStatusResponse(configured=configured, sender_mode=sender_mode)


@router.post("/setup", response_model=OwnerRead)
def setup_owner(owner_in: OwnerSetup, db: Session = Depends(get_db)):
    try:
        owner = create_owner(db, owner_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not owner:
        raise HTTPException(status_code=409, detail="Owner account already exists")
    return owner


@router.post("/login", response_model=OwnerLoginResponse)
def login(owner_in: OwnerLogin, db: Session = Depends(get_db)):
    try:
        phone = normalize_owner_phone(owner_in.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    login_result = login_owner(db, phone, owner_in.password)
    if not login_result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone or password")
    owner = login_result["owner"]
    if bool(owner.is_blocked):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner account is blocked")
    if login_result["actor_type"] == "owner_admin":
        token = create_owner_admin_access_token(owner, login_result["actor_id"], login_result["actor_name"])
    else:
        token = create_owner_access_token(owner)
    return OwnerLoginResponse(
        access_token=token,
        actor_type=login_result["actor_type"],
        actor_name=login_result["actor_name"],
        owner=OwnerRead.model_validate(owner),
    )


@router.patch("/profile", response_model=OwnerRead)
def update_profile(
    owner_in: OwnerUpdate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    try:
        owner = update_owner(db, owner_in, current_owner.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not owner:
        raise HTTPException(status_code=404, detail="Owner account not set up")
    return owner


@router.post("/password-reset/request", response_model=OwnerPasswordResetRequestResponse)
def request_password_reset(payload: OwnerPasswordResetRequest, db: Session = Depends(get_db)):
    identifier = (payload.phone or "").strip()
    # Return a generic message even when identifier is missing or unknown to avoid account enumeration.
    if not identifier:
        return OwnerPasswordResetRequestResponse(message="If the account exists, a reset link has been sent.")

    raw_token = request_owner_password_reset(db, identifier)
    response = OwnerPasswordResetRequestResponse(message="If the account exists, a reset link has been sent.")
    if raw_token and EXPOSE_RESET_TOKEN:
        response.reset_token = raw_token
    return response


@router.post("/password-reset/confirm", response_model=OwnerPasswordResetConfirmResponse)
def confirm_password_reset(payload: OwnerPasswordResetConfirm, db: Session = Depends(get_db)):
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")

    ok = confirm_owner_password_reset(db, payload.token, payload.new_password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    return OwnerPasswordResetConfirmResponse(message="Password has been reset successfully")


@router.post("/register-phone", response_model=OwnerRegisterPhoneResponse)
def register_phone(payload: OwnerRegisterPhoneRequest, db: Session = Depends(get_db)):
    try:
        phone = normalize_owner_phone(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    ok = register_owner_phone(db, phone, payload.password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid owner password")
    return OwnerRegisterPhoneResponse(message="Owner login phone registered successfully")


@router.get("/admins", response_model=list[OwnerAdminRead])
def get_owner_admins(
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return list_owner_admins(db, current_owner.id)


@router.post("/admins/invite", response_model=OwnerAdminRead)
def owner_invite_admin(
    payload: OwnerAdminInviteRequest,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    try:
        invite = invite_owner_admin(db, current_owner.id, payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _send_owner_admin_invite_sms(invite.phone)
    return invite


@router.post("/admin-invitations/lookup", response_model=list[OwnerAdminRead])
def owner_admin_lookup_invitations(payload: OwnerAdminInviteRequest, db: Session = Depends(get_db)):
    try:
        return lookup_owner_admin_invites(db, payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/admin-invitations/{invite_id}/accept", response_model=OwnerAdminRead)
def owner_admin_accept_invitation(
    invite_id: int,
    payload: OwnerAdminAcceptInviteRequest,
    db: Session = Depends(get_db),
):
    try:
        invite = accept_owner_admin_invite(
            db,
            invite_id,
            payload.phone,
            payload.name,
            payload.email,
            payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    return invite


@router.post("/ops/login", response_model=OwnerOpsLoginResponse)
def ops_login(payload: OwnerOpsLoginRequest):
    if not _verify_master_admin_login(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid master admin credentials")
    token = create_propify_admin_access_token(payload.username.strip())
    return OwnerOpsLoginResponse(access_token=token, username=payload.username.strip())


@router.post("/ops/block-by-phone", response_model=OwnerOperationResponse)
def block_owner(
    payload: OwnerBlockByPhoneRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_propify_admin),
):
    _ = current_admin
    try:
        ok = block_owner_by_phone(db, payload.phone, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found for phone")
    return OwnerOperationResponse(message="Owner account blocked")


@router.post("/ops/unblock-by-phone", response_model=OwnerOperationResponse)
def unblock_owner(
    payload: OwnerBlockByPhoneRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_propify_admin),
):
    _ = current_admin
    try:
        ok = unblock_owner_by_phone(db, payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found for phone")
    return OwnerOperationResponse(message="Owner account unblocked")


@router.post("/ops/status-by-phone", response_model=OwnerStatusByPhoneResponse)
def status_by_phone(
    payload: OwnerStatusByPhoneRequest,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_propify_admin),
):
    _ = current_admin
    try:
        status_payload = get_owner_status_by_phone(db, payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OwnerStatusByPhoneResponse(**status_payload)
