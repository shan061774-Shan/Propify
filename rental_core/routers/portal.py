from datetime import date
from pathlib import Path
import tempfile
import uuid
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from rental_core.auth import (
    create_contractor_access_token,
    create_tenant_access_token,
    get_current_contractor,
    get_current_tenant,
)
from rental_core.db import get_db
from rental_core.models.contractor import Contractor
from rental_core.models.lease import Lease
from rental_core.models.maintenance import MaintenanceRequest
from rental_core.models.owner import OwnerAccount
from rental_core.models.owner_contractor_link import OwnerContractorLink
from rental_core.models.owner_tenant_link import OwnerTenantLink
from rental_core.models.property import Property
from rental_core.models.tenant import Tenant
from rental_core.models.unit import Unit
from rental_core.schemas.portal import (
    ContractorLoginResponse,
    ContractorMaintenanceRead,
    ContractorMeUpdate,
    PortalManagementContext,
    ContractorRequestUpdate,
    PhoneLogin,
    TenantLeaseUnitRead,
    TenantLoginResponse,
    TenantMaintenanceRead,
    TenantMeUpdate,
    TenantRequestCreate,
    UploadPhotoResponse,
)
from rental_core.schemas.network import (
    ContractorInviteAcceptByPhone,
    InviteByPhone,
    OwnerContractorLinkRead,
    OwnerTenantLinkRead,
    TenantInviteAcceptByPhone,
)
from rental_core.schemas.contractor import ContractorRead
from rental_core.schemas.tenant import TenantRead
from rental_core.services.document_service import (
    create_document,
    get_document_path,
)
from rental_core.services.portal_service import (
    contractor_request_rows,
    create_tenant_request_scoped,
    get_tenant_document_scoped,
    list_tenant_documents_scoped,
    tenant_active_lease_rows,
    tenant_allowed_lease_ids,
    tenant_request_rows,
    update_contractor_request_status_scoped,
)
from rental_core.services.network_service import (
    accept_contractor_invite,
    accept_contractor_invite_by_phone,
    accept_tenant_invite,
    accept_tenant_invite_by_phone,
    list_contractor_invites,
    list_contractor_invites_by_phone,
    list_tenant_invites,
    list_tenant_invites_by_phone,
    link_contractor_to_phone_invites,
    link_tenant_to_phone_invites,
)

router = APIRouter(prefix="/portal", tags=["portal"])

ALLOWED_MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".avi", ".webm"}
ALLOWED_MEDIA_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
}
ALLOWED_DOC_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".doc", ".docx"}
ALLOWED_DOC_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
LOGIN_WINDOW_SECONDS = int(os.getenv("PROPIFY_PORTAL_LOGIN_WINDOW_SECONDS", "900"))
LOGIN_MAX_ATTEMPTS = int(os.getenv("PROPIFY_PORTAL_LOGIN_MAX_ATTEMPTS", "5"))

_login_attempts: dict[str, deque[float]] = defaultdict(deque)
_login_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _prune_attempts(bucket: deque[float], now: float) -> None:
    cutoff = now - LOGIN_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()


def _check_login_rate_limit(route_key: str, phone: str, ip: str) -> None:
    now = time.time()
    phone_key = f"{route_key}:phone:{phone.lower()}"
    ip_key = f"{route_key}:ip:{ip}"

    with _login_lock:
        phone_bucket = _login_attempts[phone_key]
        ip_bucket = _login_attempts[ip_key]
        _prune_attempts(phone_bucket, now)
        _prune_attempts(ip_bucket, now)

        if len(phone_bucket) >= LOGIN_MAX_ATTEMPTS or len(ip_bucket) >= LOGIN_MAX_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")


def _record_login_failure(route_key: str, phone: str, ip: str) -> None:
    now = time.time()
    phone_key = f"{route_key}:phone:{phone.lower()}"
    ip_key = f"{route_key}:ip:{ip}"

    with _login_lock:
        phone_bucket = _login_attempts[phone_key]
        ip_bucket = _login_attempts[ip_key]
        _prune_attempts(phone_bucket, now)
        _prune_attempts(ip_bucket, now)
        phone_bucket.append(now)
        ip_bucket.append(now)


def _clear_login_attempts(route_key: str, phone: str, ip: str) -> None:
    phone_key = f"{route_key}:phone:{phone.lower()}"
    ip_key = f"{route_key}:ip:{ip}"
    with _login_lock:
        _login_attempts.pop(phone_key, None)
        _login_attempts.pop(ip_key, None)


def _normalize_phone(value: str) -> str:
    return (value or "").strip()


def _save_media_upload(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_MEDIA_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")

    if file.content_type and file.content_type.lower() not in ALLOWED_MEDIA_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    upload_dir = Path("uploads/maintenance")
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{suffix}"
    destination = upload_dir / filename
    with open(destination, "wb") as handle:
        handle.write(content)

    return f"uploads/maintenance/{filename}"


def _to_tenant_request_read(req, unit, prop) -> TenantMaintenanceRead:
    return TenantMaintenanceRead(
        id=req.id,
        unit_id=req.unit_id,
        unit_number=str(unit.unit_number),
        property_name=prop.name,
        property_address=prop.address,
        description=req.description,
        priority=req.priority,
        status=req.status,
        photo_path=req.photo_path,
        request_date=req.request_date,
        closed_date=req.closed_date,
    )


def _to_contractor_request_read(req, unit, prop) -> ContractorMaintenanceRead:
    return ContractorMaintenanceRead(
        id=req.id,
        unit_id=req.unit_id,
        unit_number=str(unit.unit_number),
        property_name=prop.name,
        property_address=prop.address,
        description=req.description,
        priority=req.priority,
        status=req.status,
        photo_path=req.photo_path,
        request_date=req.request_date,
        closed_date=req.closed_date,
    )


def _management_context_from_rows(rows) -> PortalManagementContext:
    company_names = sorted({(company or "").strip() for company, _ in rows if (company or "").strip()})
    owner_names = sorted({(owner or "").strip() for _, owner in rows if (owner or "").strip()})
    return PortalManagementContext(company_names=company_names, owner_names=owner_names)


@router.post("/tenant/login", response_model=TenantLoginResponse)
def tenant_login(payload: PhoneLogin, request: Request, db: Session = Depends(get_db)):
    phone = _normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")

    ip = _client_ip(request)
    _check_login_rate_limit("tenant_login", phone, ip)

    tenant = db.query(Tenant).filter(Tenant.phone == phone).first()
    if not tenant:
        _record_login_failure("tenant_login", phone, ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login credentials")

    link_tenant_to_phone_invites(db, tenant)

    token = create_tenant_access_token(tenant)
    _clear_login_attempts("tenant_login", phone, ip)
    return TenantLoginResponse(access_token=token, tenant=tenant)


@router.get("/tenant/me", response_model=TenantRead)
def tenant_me(current_tenant: Tenant = Depends(get_current_tenant)):
    return current_tenant


@router.get("/tenant/management-context", response_model=PortalManagementContext)
def tenant_management_context(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    link_rows = (
        db.query(OwnerAccount.company_name, OwnerAccount.owner_name)
        .join(OwnerTenantLink, OwnerTenantLink.owner_id == OwnerAccount.id)
        .filter(
            OwnerTenantLink.tenant_id == current_tenant.id,
            OwnerTenantLink.status == "approved",
        )
        .distinct()
        .all()
    )

    lease_rows = (
        db.query(OwnerAccount.company_name, OwnerAccount.owner_name)
        .join(Property, Property.owner_id == OwnerAccount.id)
        .join(Unit, Unit.property_id == Property.id)
        .join(Lease, Lease.unit_id == Unit.id)
        .filter(Lease.tenant_id == current_tenant.id)
        .distinct()
        .all()
    )

    rows = list({(company, owner) for company, owner in [*link_rows, *lease_rows]})
    return _management_context_from_rows(rows)


@router.get("/tenant/invitations", response_model=list[OwnerTenantLinkRead])
def tenant_my_invitations(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return list_tenant_invites(db, current_tenant.id)


@router.post("/tenant/invitations/lookup", response_model=list[OwnerTenantLinkRead])
def tenant_lookup_invitations(payload: InviteByPhone, db: Session = Depends(get_db)):
    phone = _normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")
    return list_tenant_invites_by_phone(db, phone)


@router.post("/tenant/invitations/{link_id}/accept", response_model=OwnerTenantLinkRead)
def tenant_accept_invitation(
    link_id: int,
    payload: TenantInviteAcceptByPhone,
    db: Session = Depends(get_db),
):
    link = accept_tenant_invite_by_phone(
        db,
        link_id=link_id,
        phone=payload.phone,
        name=payload.name,
        email=payload.email,
    )
    if not link:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return link


@router.post("/tenant/invitations/{link_id}/accept-auth", response_model=OwnerTenantLinkRead)
def tenant_accept_invitation_authenticated(
    link_id: int,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    link = accept_tenant_invite(db, tenant_id=current_tenant.id, link_id=link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return link


@router.patch("/tenant/me", response_model=TenantRead)
def tenant_me_update(
    payload: TenantMeUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_tenant, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(current_tenant)
    return current_tenant


@router.get("/tenant/leases", response_model=list[TenantLeaseUnitRead])
def tenant_leases(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    rows = tenant_active_lease_rows(db, current_tenant.id)
    return [
        TenantLeaseUnitRead(
            lease_id=lease.id,
            lease_number=lease.lease_number,
            unit_id=unit.id,
            unit_number=str(unit.unit_number),
            property_name=prop.name,
            property_address=prop.address,
        )
        for lease, unit, prop in rows
    ]


@router.get("/tenant/requests", response_model=list[TenantMaintenanceRead])
def tenant_requests(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return [_to_tenant_request_read(req, unit, prop) for req, unit, prop in tenant_request_rows(db, current_tenant.id)]


@router.post("/tenant/requests", response_model=TenantMaintenanceRead)
def tenant_create_request(
    payload: TenantRequestCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    created = create_tenant_request_scoped(
        db=db,
        tenant_id=current_tenant.id,
        unit_id=payload.unit_id,
        description=payload.description.strip(),
        priority=payload.priority,
        photo_path=payload.photo_path,
    )
    if not created:
        raise HTTPException(status_code=403, detail="Unit does not belong to tenant")
    req, unit, prop = created
    return _to_tenant_request_read(req, unit, prop)


@router.post("/tenant/upload-photo", response_model=UploadPhotoResponse)
def tenant_upload_photo(
    file: UploadFile = File(...),
    current_tenant: Tenant = Depends(get_current_tenant),
):
    # current_tenant dependency enforces tenant authentication.
    _ = current_tenant
    return UploadPhotoResponse(photo_path=_save_media_upload(file))


@router.get("/tenant/documents")
def tenant_documents(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return list_tenant_documents_scoped(db, current_tenant.id)


@router.post("/tenant/documents/upload")
def tenant_upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    lease_id: int | None = Form(default=None),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_DOC_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")

    if file.content_type and file.content_type.lower() not in ALLOWED_DOC_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    allowed_lease_ids = tenant_allowed_lease_ids(db, current_tenant.id)
    if lease_id is not None and lease_id not in allowed_lease_ids:
        raise HTTPException(status_code=403, detail="Lease does not belong to tenant")

    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        temp_path = Path(tmp.name)

    try:
        doc = create_document(
            db=db,
            source_path=temp_path,
            original_filename=file.filename,
            content_type=file.content_type,
            document_type=document_type,
            lease_id=lease_id,
            tenant_id=current_tenant.id,
        )
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return doc


@router.get("/tenant/documents/{document_id}/download")
def tenant_download_document(
    document_id: int,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    doc = get_tenant_document_scoped(db, current_tenant.id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = get_document_path(doc.stored_filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stored file not found")

    return FileResponse(
        path=file_path,
        media_type=doc.content_type or "application/octet-stream",
        filename=doc.original_filename,
    )


@router.post("/contractor/login", response_model=ContractorLoginResponse)
def contractor_login(payload: PhoneLogin, request: Request, db: Session = Depends(get_db)):
    phone = _normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")

    ip = _client_ip(request)
    _check_login_rate_limit("contractor_login", phone, ip)

    contractor = db.query(Contractor).filter(Contractor.phone == phone).first()
    if not contractor:
        _record_login_failure("contractor_login", phone, ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login credentials")

    link_contractor_to_phone_invites(db, contractor)

    token = create_contractor_access_token(contractor)
    _clear_login_attempts("contractor_login", phone, ip)
    return ContractorLoginResponse(access_token=token, contractor=contractor)


@router.get("/contractor/me", response_model=ContractorRead)
def contractor_me(current_contractor: Contractor = Depends(get_current_contractor)):
    return current_contractor


@router.get("/contractor/management-context", response_model=PortalManagementContext)
def contractor_management_context(
    current_contractor: Contractor = Depends(get_current_contractor),
    db: Session = Depends(get_db),
):
    link_rows = (
        db.query(OwnerAccount.company_name, OwnerAccount.owner_name)
        .join(OwnerContractorLink, OwnerContractorLink.owner_id == OwnerAccount.id)
        .filter(
            OwnerContractorLink.contractor_id == current_contractor.id,
            OwnerContractorLink.status == "approved",
        )
        .distinct()
        .all()
    )

    work_rows = (
        db.query(OwnerAccount.company_name, OwnerAccount.owner_name)
        .join(Property, Property.owner_id == OwnerAccount.id)
        .join(Unit, Unit.property_id == Property.id)
        .join(MaintenanceRequest, MaintenanceRequest.unit_id == Unit.id)
        .filter(MaintenanceRequest.contractor_id == current_contractor.id)
        .distinct()
        .all()
    )

    rows = list({(company, owner) for company, owner in [*link_rows, *work_rows]})
    return _management_context_from_rows(rows)


@router.get("/contractor/invitations", response_model=list[OwnerContractorLinkRead])
def contractor_my_invitations(
    current_contractor: Contractor = Depends(get_current_contractor),
    db: Session = Depends(get_db),
):
    return list_contractor_invites(db, current_contractor.id)


@router.post("/contractor/invitations/lookup", response_model=list[OwnerContractorLinkRead])
def contractor_lookup_invitations(payload: InviteByPhone, db: Session = Depends(get_db)):
    phone = _normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")
    return list_contractor_invites_by_phone(db, phone)


@router.post("/contractor/invitations/{link_id}/accept", response_model=OwnerContractorLinkRead)
def contractor_accept_invitation(
    link_id: int,
    payload: ContractorInviteAcceptByPhone,
    db: Session = Depends(get_db),
):
    link = accept_contractor_invite_by_phone(
        db,
        link_id=link_id,
        phone=payload.phone,
        name=payload.name,
        email=payload.email,
        specialty=payload.specialty,
    )
    if not link:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return link


@router.post("/contractor/invitations/{link_id}/accept-auth", response_model=OwnerContractorLinkRead)
def contractor_accept_invitation_authenticated(
    link_id: int,
    current_contractor: Contractor = Depends(get_current_contractor),
    db: Session = Depends(get_db),
):
    link = accept_contractor_invite(db, contractor_id=current_contractor.id, link_id=link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return link


@router.patch("/contractor/me", response_model=ContractorRead)
def contractor_me_update(
    payload: ContractorMeUpdate,
    current_contractor: Contractor = Depends(get_current_contractor),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_contractor, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(current_contractor)
    return current_contractor


@router.get("/contractor/requests", response_model=list[ContractorMaintenanceRead])
def contractor_requests(
    current_contractor: Contractor = Depends(get_current_contractor),
    db: Session = Depends(get_db),
):
    rows = contractor_request_rows(db, current_contractor.id)
    return [_to_contractor_request_read(req, unit, prop) for req, unit, prop in rows]


@router.patch("/contractor/requests/{request_id}", response_model=ContractorMaintenanceRead)
def contractor_update_request(
    request_id: int,
    payload: ContractorRequestUpdate,
    current_contractor: Contractor = Depends(get_current_contractor),
    db: Session = Depends(get_db),
):
    if payload.status not in {"open", "in_progress", "closed"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    updated = update_contractor_request_status_scoped(db, current_contractor.id, request_id, payload.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Request not found")
    req, unit, prop = updated
    return _to_contractor_request_read(req, unit, prop)
