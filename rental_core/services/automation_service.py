from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from infra.send_rent_due_sms import build_reminder_message, get_twilio_client, send_sms_message
from rental_core.models.lease import Lease
from rental_core.models.payment import Payment
from rental_core.models.property import Property
from rental_core.models.unit import Unit
from rental_core.services.network_service import list_owner_tenants


def _is_active_lease(lease: Lease, current_day: date) -> bool:
    if lease.status != "active":
        return False
    if lease.start_date and lease.start_date > current_day:
        return False
    if lease.end_date and lease.end_date < current_day:
        return False
    return True


def _monthly_paid(db: Session, lease_id: int, current_day: date) -> float:
    payments = db.query(Payment).filter(Payment.lease_id == lease_id).all()
    return sum(
        float(payment.amount or 0)
        for payment in payments
        if payment.date.year == current_day.year and payment.date.month == current_day.month
    )


def _tenant_due_breakdown(db: Session, owner_id: int, tenant_id: int, current_day: date) -> tuple[int, float, float, float]:
    lease_rows = (
        db.query(Lease, Unit, Property)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .filter(Lease.tenant_id == tenant_id, Property.owner_id == owner_id)
        .all()
    )

    lease_count = 0
    rent_due = 0.0
    late_fee = 0.0

    for lease, unit, prop in lease_rows:
        if not _is_active_lease(lease, current_day):
            continue

        lease_count += 1
        monthly_rent = float(unit.rent_amount or 0)
        paid_this_month = _monthly_paid(db, lease.id, current_day)
        remaining_due = max(monthly_rent - paid_this_month, 0.0)
        rent_due += remaining_due

        grace_days = int(prop.grace_period_days or 3)
        property_late_fee = float(prop.late_fee_amount or 30)
        if current_day.day > grace_days and remaining_due > 0:
            late_fee += property_late_fee

    total_due = rent_due + late_fee
    return lease_count, rent_due, late_fee, total_due


def build_rent_reminder_preview(db: Session, owner_id: int) -> dict:
    today = date.today()
    tenants = list_owner_tenants(db, owner_id)

    items: list[dict] = []
    ready_to_send = 0
    with_due = 0

    for tenant in tenants:
        lease_count, rent_due, late_fee, total_due = _tenant_due_breakdown(db, owner_id, tenant.id, today)
        if total_due <= 0:
            continue

        with_due += 1
        phone = (tenant.phone or "").strip()
        if phone:
            ready_to_send += 1

        items.append(
            {
                "tenant_id": tenant.id,
                "tenant_name": tenant.name,
                "tenant_phone": phone,
                "lease_count": lease_count,
                "rent_due": round(rent_due, 2),
                "late_fee": round(late_fee, 2),
                "total_due": round(total_due, 2),
                "message": build_reminder_message(tenant, total_due, late_fee),
            }
        )

    items.sort(key=lambda row: row["total_due"], reverse=True)

    return {
        "run_date": today,
        "total_candidates": len(tenants),
        "total_with_due": with_due,
        "total_ready_to_send": ready_to_send,
        "items": items,
    }


def run_rent_reminder_agent(db: Session, owner_id: int, dry_run: bool = True, max_messages: int = 100) -> dict:
    preview = build_rent_reminder_preview(db, owner_id)
    items = preview["items"]

    capped_items = items[: max(1, int(max_messages or 1))]
    details: list[str] = []
    sent = 0
    skipped_no_phone = 0
    failures = 0

    client = None
    from_number = None
    messaging_service_sid = None
    if not dry_run:
        client, from_number, messaging_service_sid = get_twilio_client()

    for item in capped_items:
        phone = (item.get("tenant_phone") or "").strip()
        name = item.get("tenant_name") or "Tenant"

        if not phone:
            skipped_no_phone += 1
            details.append(f"SKIP {name}: missing phone")
            continue

        if dry_run:
            sent += 1
            details.append(f"DRY-RUN {name}: would send to {phone}")
            continue

        try:
            send_sms_message(
                client,
                phone,
                item["message"],
                from_number=from_number,
                messaging_service_sid=messaging_service_sid,
            )
            sent += 1
            details.append(f"SENT {name}: {phone}")
        except Exception as exc:
            failures += 1
            details.append(f"FAIL {name}: {exc}")

    return {
        "run_date": preview["run_date"],
        "dry_run": dry_run,
        "considered": len(items),
        "queued": len(capped_items),
        "sent": sent,
        "skipped_no_phone": skipped_no_phone,
        "failures": failures,
        "details": details,
    }
