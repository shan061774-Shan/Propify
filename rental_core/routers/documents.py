from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.document import DocumentRead
from rental_core.services.document_service import (
    create_document,
    delete_document_owner_scoped,
    get_document_owner_scoped,
    get_document_path,
    list_documents_by_lease_owner_scoped,
    list_documents_by_tenant_owner_scoped,
)


router = APIRouter(prefix="/documents", tags=["documents"])
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".doc", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.get("/lease/{lease_id}", response_model=list[DocumentRead])
def get_lease_documents(
    lease_id: int,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return list_documents_by_lease_owner_scoped(db, lease_id, current_owner.id)


@router.get("/tenant/{tenant_id}", response_model=list[DocumentRead])
def get_tenant_documents(
    tenant_id: int,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return list_documents_by_tenant_owner_scoped(db, tenant_id, current_owner.id)


@router.post("/upload", response_model=DocumentRead)
def upload_document(
    file: UploadFile = File(...),
    lease_id: int | None = Form(default=None),
    tenant_id: int | None = Form(default=None),
    document_type: str | None = Form(default="other"),
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    if not lease_id and not tenant_id:
        raise HTTPException(status_code=400, detail="Provide lease_id or tenant_id")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")

    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported content type")

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
            tenant_id=tenant_id,
            owner_id=current_owner.id,
        )
    finally:
        if temp_path.exists():
            temp_path.unlink()

    if not doc:
        raise HTTPException(status_code=403, detail="You do not have access to attach document to this record")

    return doc


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    doc = get_document_owner_scoped(db, document_id, current_owner.id)
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


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_route(
    document_id: int,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    if not delete_document_owner_scoped(db, document_id, current_owner.id):
        raise HTTPException(status_code=404, detail="Document not found")
