from pathlib import Path
import shutil
import uuid

from sqlalchemy.orm import Session

from rental_core.models.document import Document
from rental_core.models.lease import Lease
from rental_core.models.owner_tenant_link import OwnerTenantLink
from rental_core.models.property import Property
from rental_core.models.unit import Unit


BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "uploaded_documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _stored_filename(original_filename: str) -> str:
    suffix = Path(original_filename).suffix
    return f"{uuid.uuid4().hex}{suffix}"


def create_document(
    db: Session,
    source_path: Path,
    original_filename: str,
    content_type: str | None,
    document_type: str | None,
    lease_id: int | None,
    tenant_id: int | None,
    owner_id: int | None = None,
):
    if owner_id is not None:
        if lease_id is not None:
            allowed_lease = (
                db.query(Lease)
                .join(Unit, Unit.id == Lease.unit_id)
                .join(Property, Property.id == Unit.property_id)
                .filter(Lease.id == lease_id, Property.owner_id == owner_id)
                .first()
            )
            if not allowed_lease:
                return None

        if tenant_id is not None:
            allowed_tenant = (
                db.query(OwnerTenantLink)
                .filter(
                    OwnerTenantLink.owner_id == owner_id,
                    OwnerTenantLink.tenant_id == tenant_id,
                    OwnerTenantLink.status == "approved",
                )
                .first()
            )
            if not allowed_tenant:
                return None

    stored_name = _stored_filename(original_filename)
    destination = UPLOAD_DIR / stored_name
    shutil.copyfile(source_path, destination)

    doc = Document(
        original_filename=original_filename,
        stored_filename=stored_name,
        content_type=content_type or "application/octet-stream",
        document_type=document_type or "other",
        lease_id=lease_id,
        tenant_id=tenant_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def list_documents_by_lease(db: Session, lease_id: int):
    return (
        db.query(Document)
        .filter(Document.lease_id == lease_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


def list_documents_by_lease_owner_scoped(db: Session, lease_id: int, owner_id: int):
    return (
        db.query(Document)
        .join(Lease, Lease.id == Document.lease_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .filter(Document.lease_id == lease_id, Property.owner_id == owner_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


def list_documents_by_tenant(db: Session, tenant_id: int):
    return (
        db.query(Document)
        .filter(Document.tenant_id == tenant_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


def list_documents_by_tenant_owner_scoped(db: Session, tenant_id: int, owner_id: int):
    return (
        db.query(Document)
        .join(
            OwnerTenantLink,
            (OwnerTenantLink.tenant_id == Document.tenant_id)
            & (OwnerTenantLink.owner_id == owner_id)
            & (OwnerTenantLink.status == "approved"),
        )
        .filter(Document.tenant_id == tenant_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


def get_document(db: Session, document_id: int):
    return db.query(Document).filter(Document.id == document_id).first()


def get_document_owner_scoped(db: Session, document_id: int, owner_id: int):
    doc = get_document(db, document_id)
    if not doc:
        return None

    if doc.lease_id is not None:
        visible_by_lease = (
            db.query(Lease)
            .join(Unit, Unit.id == Lease.unit_id)
            .join(Property, Property.id == Unit.property_id)
            .filter(Lease.id == doc.lease_id, Property.owner_id == owner_id)
            .first()
        )
        if visible_by_lease:
            return doc

    if doc.tenant_id is not None:
        visible_by_tenant = (
            db.query(OwnerTenantLink)
            .filter(
                OwnerTenantLink.owner_id == owner_id,
                OwnerTenantLink.tenant_id == doc.tenant_id,
                OwnerTenantLink.status == "approved",
            )
            .first()
        )
        if visible_by_tenant:
            return doc

    return None


def get_document_path(stored_filename: str) -> Path:
    return UPLOAD_DIR / stored_filename


def delete_document(db: Session, document_id: int) -> bool:
    doc = get_document(db, document_id)
    if not doc:
        return False

    file_path = get_document_path(doc.stored_filename)
    if file_path.exists():
        file_path.unlink()

    db.delete(doc)
    db.commit()
    return True


def delete_document_owner_scoped(db: Session, document_id: int, owner_id: int) -> bool:
    doc = get_document_owner_scoped(db, document_id, owner_id)
    if not doc:
        return False

    file_path = get_document_path(doc.stored_filename)
    if file_path.exists():
        file_path.unlink()

    db.delete(doc)
    db.commit()
    return True
