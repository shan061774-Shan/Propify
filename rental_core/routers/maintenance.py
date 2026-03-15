import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.maintenance import MaintenanceCreate, MaintenanceRead, MaintenanceUpdate
from rental_core.services.maintenance_service import list_requests, create_request, update_request, delete_request

UPLOAD_DIR = Path("uploads/maintenance")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".avi", ".webm"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

@router.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")

    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{suffix}"
    dest = UPLOAD_DIR / filename
    with open(dest, "wb") as f:
        f.write(content)
    return {"photo_path": f"uploads/maintenance/{filename}"}


@router.get("/", response_model=list[MaintenanceRead])
def get_requests(db: Session = Depends(get_db), current_owner: OwnerAccount = Depends(get_current_owner)):
    return list_requests(db, current_owner.id)

@router.post("/", response_model=MaintenanceRead)
def create_request_route(
    req_in: MaintenanceCreate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    req = create_request(db, req_in, current_owner.id)
    if not req:
        raise HTTPException(status_code=404, detail="Unit not found")
    return req

@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request_route(
    request_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    if not delete_request(db, request_id, current_owner.id):
        raise HTTPException(status_code=404, detail="Maintenance request not found")

@router.patch("/{request_id}", response_model=MaintenanceRead)
def update_request_route(
    request_id: int,
    req_in: MaintenanceUpdate,
    db: Session = Depends(get_db),
    current_owner: OwnerAccount = Depends(get_current_owner),
):
    req = update_request(db, request_id, req_in, current_owner.id)
    if not req:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    return req
