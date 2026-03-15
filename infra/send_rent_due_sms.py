from __future__ import annotations

import os
from datetime import date

from dotenv import load_dotenv
from twilio.rest import Client

from rental_core.db import SessionLocal
from rental_core.models.property import Property
from rental_core.models.lease import Lease
from rental_core.models.payment import Payment
from rental_core.models.tenant import Tenant
from rental_core.models.unit import Unit


def is_active_lease(lease: Lease, current_day: date) -> bool:
    if lease.status != "active":
        return False
    if lease.start_date and lease.start_date > current_day:
        return False
    if lease.end_date and lease.end_date < current_day:
        return False
    return True


def monthly_paid(db, lease_id: int, current_day: date) -> float:
    payments = db.query(Payment).filter(Payment.lease_id == lease_id).all()
    return sum(
        float(payment.amount or 0)
        for payment in payments
        if payment.date.year == current_day.year and payment.date.month == current_day.month
    )


def tenant_due_amount(db, tenant: Tenant, current_day: date) -> tuple[float, float, float]:
    leases = db.query(Lease).filter(Lease.tenant_id == tenant.id).all()
    rent_due = 0.0
    paid = 0.0
    late_fee = 0.0

    for lease in leases:
        if not is_active_lease(lease, current_day):
            continue
        unit = db.query(Unit).filter(Unit.id == lease.unit_id).first()
        prop = db.query(Property).filter(Property.id == unit.property_id).first() if unit else None
        monthly_rent = float(unit.rent_amount or 0) if unit else 0.0
        paid_this_month = monthly_paid(db, lease.id, current_day)
        paid += paid_this_month
        remaining_due = max(monthly_rent - paid_this_month, 0.0)
        rent_due += remaining_due

        grace_days = int(prop.grace_period_days if prop else 3)
        property_late_fee = float(prop.late_fee_amount if prop else 30)
        if current_day.day > grace_days and remaining_due > 0:
            late_fee += property_late_fee

    return rent_due, late_fee, rent_due + late_fee


def build_reminder_message(tenant: Tenant | dict, total_due: float, late_fee: float) -> str:
    tenant_name = tenant.name if hasattr(tenant, "name") else str(tenant.get("name", "Tenant"))
    message = (
        f"Good morning {tenant_name}, your current rent balance is ${total_due:,.2f}. "
        f"Rent is due on the 1st of each month."
    )
    if late_fee > 0:
        message += f" This includes ${late_fee:,.2f} in late fees."
    return message


def get_twilio_client() -> tuple[Client, str]:
    load_dotenv()

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not account_sid or not auth_token or not from_number:
        raise RuntimeError("Twilio environment variables are not configured")

    return Client(account_sid, auth_token), from_number


def send_reminder_to_tenant(tenant_id: int) -> str:
    client, from_number = get_twilio_client()
    db = SessionLocal()

    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise RuntimeError("Tenant not found")
        if not tenant.phone:
            raise RuntimeError("Tenant phone number is missing")

        today = date.today()
        _, late_fee, total_due = tenant_due_amount(db, tenant, today)
        if total_due <= 0:
            return f"No reminder sent. {tenant.name} has no balance due today."

        message = build_reminder_message(tenant, total_due, late_fee)
        client.messages.create(body=message, from_=from_number, to=tenant.phone)
        return f"Reminder sent to {tenant.name} at {tenant.phone}."
    finally:
        db.close()


def main() -> None:
    client, from_number = get_twilio_client()
    db = SessionLocal()

    try:
        today = date.today()
        tenants = db.query(Tenant).all()
        for tenant in tenants:
            if not tenant.phone:
                continue

            rent_due, late_fee, total_due = tenant_due_amount(db, tenant, today)
            if total_due <= 0:
                continue

            message = build_reminder_message(tenant, total_due, late_fee)

            client.messages.create(
                body=message,
                from_=from_number,
                to=tenant.phone,
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()