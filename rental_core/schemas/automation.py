from datetime import date

from pydantic import BaseModel


class RentReminderCandidate(BaseModel):
    tenant_id: int
    tenant_name: str
    tenant_phone: str | None = ""
    lease_count: int
    rent_due: float
    late_fee: float
    total_due: float
    message: str


class RentReminderPreviewResponse(BaseModel):
    run_date: date
    total_candidates: int
    total_with_due: int
    total_ready_to_send: int
    items: list[RentReminderCandidate]


class RentReminderRunRequest(BaseModel):
    dry_run: bool = True
    max_messages: int = 100


class RentReminderRunResponse(BaseModel):
    run_date: date
    dry_run: bool
    considered: int
    queued: int
    sent: int
    skipped_no_phone: int
    failures: int
    details: list[str]
