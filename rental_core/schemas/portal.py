from datetime import date

from pydantic import BaseModel, ConfigDict

from rental_core.schemas.contractor import ContractorRead, ContractorUpdate
from rental_core.schemas.document import DocumentRead
from rental_core.schemas.tenant import TenantRead, TenantUpdate


class PhoneLogin(BaseModel):
    phone: str


class TenantLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant: TenantRead


class ContractorLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    contractor: ContractorRead


class PortalManagementContext(BaseModel):
    company_names: list[str] = []
    owner_names: list[str] = []


class TenantRequestCreate(BaseModel):
    unit_id: int
    description: str
    priority: str = "low"
    photo_path: str | None = None


class ContractorRequestUpdate(BaseModel):
    status: str


class TenantLeaseUnitRead(BaseModel):
    lease_id: int
    lease_number: str
    unit_id: int
    unit_number: str
    property_name: str
    property_address: str


class TenantMaintenanceRead(BaseModel):
    id: int
    unit_id: int
    unit_number: str
    property_name: str
    property_address: str
    description: str
    priority: str
    status: str
    photo_path: str | None = None
    request_date: date
    closed_date: date | None = None


class ContractorMaintenanceRead(BaseModel):
    id: int
    unit_id: int
    unit_number: str
    property_name: str
    property_address: str
    description: str
    priority: str
    status: str
    photo_path: str | None = None
    request_date: date
    closed_date: date | None = None


class UploadPhotoResponse(BaseModel):
    photo_path: str


class TenantMeUpdate(TenantUpdate):
    model_config = ConfigDict(extra="forbid")


class ContractorMeUpdate(ContractorUpdate):
    model_config = ConfigDict(extra="forbid")


class TenantDocumentUploadResponse(DocumentRead):
    pass
