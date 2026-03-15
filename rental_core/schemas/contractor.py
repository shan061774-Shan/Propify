from pydantic import BaseModel, ConfigDict


class ContractorBase(BaseModel):
    name: str
    phone: str | None = ""
    email: str | None = ""
    specialty: str | None = ""
    notes: str | None = ""


class ContractorCreate(ContractorBase):
    pass


class ContractorUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    specialty: str | None = None
    notes: str | None = None


class ContractorRead(ContractorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
