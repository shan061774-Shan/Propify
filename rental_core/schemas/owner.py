from pydantic import BaseModel, ConfigDict


class OwnerBase(BaseModel):
    company_name: str
    company_address: str | None = ""
    company_phone: str | None = ""
    owner_name: str
    owner_email: str | None = ""
    owner_phone: str | None = ""


class OwnerSetup(OwnerBase):
    username: str | None = None
    password: str


class OwnerLogin(BaseModel):
    phone: str
    password: str


class OwnerStatus(BaseModel):
    is_setup: bool


class OwnerUpdate(BaseModel):
    company_name: str | None = None
    company_address: str | None = None
    company_phone: str | None = None
    owner_name: str | None = None
    owner_email: str | None = None
    owner_phone: str | None = None
    two_fa_enabled: bool | None = None


class OwnerRead(OwnerBase):
    id: int
    username: str
    two_fa_enabled: bool = False
    is_blocked: bool = False
    blocked_reason: str | None = ""

    model_config = ConfigDict(from_attributes=True)


class OwnerLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    owner: OwnerRead


class OwnerPasswordResetRequest(BaseModel):
    phone: str | None = None


class OwnerPasswordResetRequestResponse(BaseModel):
    message: str
    reset_token: str | None = None


class OwnerPasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class OwnerPasswordResetConfirmResponse(BaseModel):
    message: str


class OwnerBlockByPhoneRequest(BaseModel):
    phone: str
    reason: str | None = None


class OwnerOperationResponse(BaseModel):
    message: str


class OwnerStatusByPhoneRequest(BaseModel):
    phone: str


class OwnerStatusByPhoneResponse(BaseModel):
    found: bool
    phone: str
    username: str | None = None
    is_blocked: bool | None = None
    blocked_reason: str | None = ""


class OwnerRegisterPhoneRequest(BaseModel):
    phone: str
    password: str


class OwnerRegisterPhoneResponse(BaseModel):
    message: str
