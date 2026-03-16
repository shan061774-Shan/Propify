from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from rental_core.auth import get_current_owner
from rental_core.db import get_db
from rental_core.models.owner import OwnerAccount
from rental_core.schemas.automation import (
    RentReminderPreviewResponse,
    RentReminderRunRequest,
    RentReminderRunResponse,
)
from rental_core.services.automation_service import (
    build_rent_reminder_preview,
    run_rent_reminder_agent,
)

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/rent-reminders/preview", response_model=RentReminderPreviewResponse)
def rent_reminder_preview(
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return build_rent_reminder_preview(db, current_owner.id)


@router.post("/rent-reminders/run", response_model=RentReminderRunResponse)
def run_rent_reminders(
    payload: RentReminderRunRequest,
    current_owner: OwnerAccount = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    try:
        return run_rent_reminder_agent(
            db,
            current_owner.id,
            dry_run=payload.dry_run,
            max_messages=payload.max_messages,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
