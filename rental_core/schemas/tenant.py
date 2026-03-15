from pydantic import BaseModel
from typing import Optional
from pydantic import ConfigDict

class TenantCreate(BaseModel):
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class TenantRead(TenantCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
