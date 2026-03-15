from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InviteByPhone(BaseModel):
    phone: str


class TenantInviteAcceptByPhone(BaseModel):
    phone: str
    name: str
    email: str | None = ""


class ContractorInviteAcceptByPhone(BaseModel):
    phone: str
    name: str
    email: str | None = ""
    specialty: str | None = ""


class OwnerTenantLinkRead(BaseModel):
    id: int
    owner_id: int
    tenant_id: int | None = None
    phone: str
    status: str
    invited_at: datetime
    accepted_at: datetime | None = None
    approved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class OwnerContractorLinkRead(BaseModel):
    id: int
    owner_id: int
    contractor_id: int | None = None
    phone: str
    status: str
    invited_at: datetime
    accepted_at: datetime | None = None
    approved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
