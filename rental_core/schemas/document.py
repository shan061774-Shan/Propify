from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    id: int
    original_filename: str
    content_type: str | None = None
    document_type: str | None = None
    uploaded_at: datetime
    lease_id: int | None = None
    tenant_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
