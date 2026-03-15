import streamlit as st
from collections import defaultdict
from datetime import date
from ui_admin.api_client import api_delete, api_get, api_post
from ui_admin.auth_guard import render_company_context, require_owner_login
from ui_admin.config import API_URL
UTILITY_TYPES = ["electric", "gas", "water", "trash", "other"]

st.set_page_config(page_title="Payments | Propify", page_icon="🏢")
st.title("💵 Payments")
require_owner_login()
render_company_context()

# load all data
props_r = api_get(f"{API_URL}/properties/")
units_r = api_get(f"{API_URL}/units/")
tenants_r = api_get(f"{API_URL}/tenants/")
leases_r = api_get(f"{API_URL}/leases/")
payments_r = api_get(f"{API_URL}/payments/")
utility_charges_r = api_get(f"{API_URL}/utility-charges/")

if not props_r.ok or not units_r.ok or not tenants_r.ok or not leases_r.ok:
    st.error("Failed to load required data")
    st.write("properties:", props_r.status_code)
    st.write("units:", units_r.status_code)
    st.write("tenants:", tenants_r.status_code)
    st.write("leases:", leases_r.status_code)
    st.stop()

properties = {p["id"]: p for p in props_r.json()}
units = {u["id"]: u for u in units_r.json()}
tenants = {t["id"]: t for t in tenants_r.json()}
leases = leases_r.json()
payments = payments_r.json() if payments_r.ok else []
utility_charges = utility_charges_r.json() if utility_charges_r.ok else []


def parse_date_value(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def monthly_paid_for_lease(lease_id: int, current_day: date) -> float:
    total = 0.0
    for payment in payments:
        if payment.get("lease_id") != lease_id:
            continue
        payment_day = parse_date_value(payment.get("date"))
        if not payment_day:
            continue
        if payment_day.year == current_day.year and payment_day.month == current_day.month:
            total += float(payment.get("amount", 0) or 0)
    return total


def utility_due_for_lease(lease_id: int) -> float:
    return sum(
        float(charge.get("amount", 0) or 0)
        for charge in utility_charges
        if charge.get("lease_id") == lease_id and not charge.get("is_paid", False)
    )

# build lease display map
def lease_label(l):
    unit = units.get(l["unit_id"], {})
    tenant = tenants.get(l["tenant_id"], {})
    prop = properties.get(unit.get("property_id"), {})
    return (
        f"Lease {l['lease_number']} | "
        f"{prop.get('name', 'Unknown')} — Unit #{unit.get('unit_number', '?')} | "
        f"Tenant: {tenant.get('name', 'Unknown')} | "
        f"{l['start_date']} → {l['end_date']} | "
        f"Status: {l['status']}"
    )

lease_options = {lease_label(l): l["id"] for l in leases}

# ── Existing Payments ────────────────────────────────────────────────────────
st.subheader("Existing Payments")
if payments:
    # group payments by property
    payments_by_prop = defaultdict(list)
    for pay in payments:
        lease = next((l for l in leases if l["id"] == pay["lease_id"]), None)
        if lease:
            unit = units.get(lease["unit_id"], {})
            prop_id = unit.get("property_id")
            payments_by_prop[prop_id].append((pay, lease))
        else:
            payments_by_prop[None].append((pay, None))

    for prop_id, items in payments_by_prop.items():
        prop = properties.get(prop_id, {})
        total = sum(p["amount"] for p, _ in items)
        st.markdown(f"### 🏠 {prop.get('name', 'Unknown Property')}")
        st.write(f"📍 {prop.get('address', '')}")
        st.write(f"Total received: **${total:,.2f}**")

        for pay, lease in items:
            unit = units.get(lease["unit_id"], {}) if lease else {}
            tenant = tenants.get(lease["tenant_id"], {}) if lease else {}
            cols = st.columns([5, 1])
            cols[0].write(
                f"Payment **#{pay['id']}**  \n"
                f"Unit: #{unit.get('unit_number', '?')} | "
                f"Tenant: {tenant.get('name', 'Unknown')}  \n"
                f"Amount: **${pay['amount']:,.2f}** | Date: {pay['date']}"
            )
            if cols[1].button("Delete", key=f"del-pay-{pay['id']}"):
                dr = api_delete(f"{API_URL}/payments/{pay['id']}")
                if dr.status_code in (200, 204):
                    st.success("Payment deleted")
                    st.rerun()
                else:
                    st.error(f"Delete failed: {dr.status_code} {dr.text}")
        st.divider()
else:
    st.info("No payments recorded yet.")

# ── Add New Payment ───────────────────────────────────────────────────────────
st.subheader("Add New Payment")

if not leases:
    st.warning("No leases found. Create a lease first.")
    st.stop()

selected_lease_label = st.selectbox("Select Lease", list(lease_options.keys()))
lease_id = lease_options[selected_lease_label]

# show lease summary
selected_lease = next((l for l in leases if l["id"] == lease_id), None)
current_due = 0.0
late_fee = 0.0
utility_due = 0.0
total_due = 0.0
if selected_lease:
    unit = units.get(selected_lease["unit_id"], {})
    tenant = tenants.get(selected_lease["tenant_id"], {})
    prop = properties.get(unit.get("property_id"), {})
    st.info(
        f"🏠 **{prop.get('name', '')}** — {prop.get('address', '')}  \n"
        f"Unit: #{unit.get('unit_number', '')} | "
        f"Rent: **${unit.get('rent_amount', 0):,.2f}**  \n"
        f"Tenant: **{tenant.get('name', '')}**  \n"
        f"Lease: {selected_lease['lease_number']} | Status: {selected_lease['status']}"
    )

    today = date.today()
    monthly_rent = float(unit.get("rent_amount", 0) or 0)
    paid_this_month = monthly_paid_for_lease(lease_id, today)
    # Apply payment to rent first, then to utilities so no manual paid/unpaid toggle is needed.
    base_rent_due = max(monthly_rent - paid_this_month, 0.0)

    grace_days = int(prop.get("grace_period_days", 3) or 3)
    late_fee_amount = float(prop.get("late_fee_amount", 30) or 30)
    if today.day > grace_days and base_rent_due > 0:
        late_fee = late_fee_amount

    utility_due_raw = utility_due_for_lease(lease_id)
    payment_after_rent = max(paid_this_month - monthly_rent, 0.0)
    utility_due = max(utility_due_raw - payment_after_rent, 0.0)
    current_due = base_rent_due
    total_due = current_due + late_fee + utility_due

    due_col1, due_col2, due_col3, due_col4 = st.columns(4)
    due_col1.metric("Monthly Rent", f"${monthly_rent:,.2f}")
    due_col2.metric("Paid This Month", f"${paid_this_month:,.2f}")
    due_col3.metric("Utility Due", f"${utility_due:,.2f}")
    due_col4.metric("Total Due", f"${total_due:,.2f}")

    if total_due > 0:
        st.markdown(
            f"<div style='color:#b42318;font-weight:700;'>Amount due now: ${total_due:,.2f}</div>",
            unsafe_allow_html=True,
        )
        if late_fee > 0:
            st.caption(
                f"Late fee includes ${late_fee:,.2f} (after day {grace_days})."
            )
    else:
        st.success("This lease is fully paid for the current month.")

    st.markdown("### Utility Bills / Charges")
    lease_utility_charges = [c for c in utility_charges if c.get("lease_id") == lease_id]
    if lease_utility_charges:
        for charge in sorted(lease_utility_charges, key=lambda c: c.get("bill_date", ""), reverse=True):
            charge_cols = st.columns([6, 1])
            charge_cols[0].write(
                f"{str(charge.get('utility_type', 'other')).title()} | "
                f"Amount: **${float(charge.get('amount', 0) or 0):,.2f}** | "
                f"Bill: {charge.get('bill_date')} | Due: {charge.get('due_date') or 'N/A'}"
            )

            if charge_cols[1].button("Delete", key=f"del-utility-charge-{charge['id']}"):
                dr = api_delete(f"{API_URL}/utility-charges/{charge['id']}")
                if dr.status_code in (200, 204):
                    st.success("Utility charge deleted")
                    st.rerun()
                else:
                    st.error(f"Delete failed: {dr.status_code} {dr.text}")
    else:
        st.caption("No utility charges for this lease yet.")

    add_bill_col1, add_bill_col2 = st.columns([1, 1])
    utility_type_key = f"utility-type-{lease_id}"
    utility_amount_key = f"utility-amount-{lease_id}"
    utility_file_counter_key = f"utility-file-counter-{lease_id}"
    if utility_file_counter_key not in st.session_state:
        st.session_state[utility_file_counter_key] = 0
    utility_file_key = f"utility-file-{lease_id}-{st.session_state[utility_file_counter_key]}"

    utility_type = add_bill_col1.selectbox("Utility Type", UTILITY_TYPES, key=utility_type_key)
    utility_amount = add_bill_col2.number_input(
        "Utility Amount",
        min_value=0.0,
        step=0.01,
        format="%.2f",
        key=utility_amount_key,
    )
    utility_bill_file = st.file_uploader("Upload Utility Bill (optional)", key=utility_file_key)

    st.caption("Tip: Upload bill first, then enter amount to auto-save the utility charge.")

    last_submitted_key = f"utility-last-submitted-{lease_id}"
    current_signature = (
        utility_type,
        round(float(utility_amount), 2),
        utility_bill_file.name if utility_bill_file else "",
    )

    # Allow creating the same amount again by first setting amount back to 0.
    if utility_amount == 0:
        st.session_state[last_submitted_key] = None

    if utility_amount > 0 and st.session_state.get(last_submitted_key) != current_signature:
        payload = {
            "lease_id": lease_id,
            "utility_type": utility_type,
            "description": "",
            "amount": utility_amount,
            "bill_date": date.today().isoformat(),
        }
        create_charge = api_post(f"{API_URL}/utility-charges/", json=payload)
        if create_charge.status_code not in (200, 201):
            st.error(f"Failed to add utility charge: {create_charge.status_code} {create_charge.text}")
            st.stop()

        if utility_bill_file:
            files = {
                "file": (
                    utility_bill_file.name,
                    utility_bill_file.getvalue(),
                    utility_bill_file.type or "application/octet-stream",
                )
            }
            data = {
                "lease_id": str(lease_id),
                "tenant_id": str(selected_lease["tenant_id"]),
                "document_type": f"utility_bill_{utility_type}",
            }
            upload_doc = api_post(f"{API_URL}/documents/upload", files=files, data=data)
            if upload_doc.status_code not in (200, 201):
                st.warning(f"Charge added, but bill upload failed: {upload_doc.status_code} {upload_doc.text}")

        st.session_state[last_submitted_key] = current_signature
        # Rotate uploader key so selected file clears on rerun.
        st.session_state[utility_file_counter_key] += 1
        st.success("Utility charge added")
        st.rerun()

payment_amount_key = f"payment-amount-{lease_id}"
payment_last_due_key = f"payment-last-due-{lease_id}"
if payment_amount_key not in st.session_state:
    st.session_state[payment_amount_key] = float(total_due)
    st.session_state[payment_last_due_key] = float(total_due)
else:
    previous_due = float(st.session_state.get(payment_last_due_key, total_due))
    # Keep default amount in sync with due unless user has manually edited it.
    if abs(previous_due - float(total_due)) > 0.009 and abs(float(st.session_state[payment_amount_key]) - previous_due) < 0.009:
        st.session_state[payment_amount_key] = float(total_due)
    st.session_state[payment_last_due_key] = float(total_due)

st.caption(f"Paid Date: {date.today().isoformat()}")
pay_col1, pay_col2 = st.columns([3, 1])
amount = pay_col1.number_input(
    "Total Amount ($)",
    min_value=0.0,
    format="%.2f",
    key=payment_amount_key,
)
submit_payment = pay_col2.button("Submit Payment", use_container_width=True)

if submit_payment:
    if amount <= 0:
        st.warning("Amount must be greater than 0")
    else:
        payload = {
            "lease_id": lease_id,
            "amount": amount,
            "date": date.today().isoformat(),
        }
        r = api_post(f"{API_URL}/payments/", json=payload)
        if r.status_code in (200, 201):
            st.success(f"Payment of ${amount:,.2f} recorded")
            st.session_state.pop(payment_amount_key, None)
            st.rerun()
        else:
            st.error(f"Failed to record payment: {r.status_code} {r.text}")