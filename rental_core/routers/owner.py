import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from rental_core.auth import create_owner_access_token, get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.owner import (
    OwnerBlockByPhoneRequest,
    OwnerLogin,
    OwnerLoginResponse,
    OwnerOperationResponse,
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
    login_owner,
    normalize_owner_phone,
    register_owner_phone,
    request_owner_password_reset,
    unblock_owner_by_phone,
    update_owner,
)

router = APIRouter(prefix="/owner", tags=["owner"])
EXPOSE_RESET_TOKEN = os.getenv("PROPIFY_EXPOSE_RESET_TOKEN", "1").strip().lower() in {"1", "true", "yes", "on"}
PROPIFY_ADMIN_KEY = os.getenv("PROPIFY_ADMIN_KEY", "").strip()


def _require_propify_ops_key(x_propify_admin_key: str | None) -> None:
    if not PROPIFY_ADMIN_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Propify ops key is not configured")
    if (x_propify_admin_key or "").strip() != PROPIFY_ADMIN_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Propify ops key")


@router.get("/profile", response_model=OwnerRead)
def get_owner_profile(current_owner: OwnerAccount = Depends(get_current_owner)):
    return current_owner


@router.get("/status", response_model=OwnerStatus)
def get_owner_status(db: Session = Depends(get_db)):
    return OwnerStatus(is_setup=bool(get_owner(db)))


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

    owner = login_owner(db, phone, owner_in.password)
    if not owner:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone or password")
    if bool(owner.is_blocked):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner account is blocked")
    token = create_owner_access_token(owner)
    return OwnerLoginResponse(access_token=token, owner=OwnerRead.model_validate(owner))


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


@router.post("/ops/block-by-phone", response_model=OwnerOperationResponse)
def block_owner(
    payload: OwnerBlockByPhoneRequest,
    db: Session = Depends(get_db),
    x_propify_admin_key: str | None = Header(default=None, alias="X-Propify-Admin-Key"),
):
    _require_propify_ops_key(x_propify_admin_key)
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
    x_propify_admin_key: str | None = Header(default=None, alias="X-Propify-Admin-Key"),
):
    _require_propify_ops_key(x_propify_admin_key)
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
    x_propify_admin_key: str | None = Header(default=None, alias="X-Propify-Admin-Key"),
):
    _require_propify_ops_key(x_propify_admin_key)
    try:
        status_payload = get_owner_status_by_phone(db, payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OwnerStatusByPhoneResponse(**status_payload)
