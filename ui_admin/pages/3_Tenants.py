import streamlit as st
from collections import defaultdict
from datetime import date, datetime
from ui_admin.api_client import api_delete, api_get, api_patch, api_post
from ui_admin.auth_guard import render_company_context, require_owner_login
from ui_admin.config import API_URL

from infra.send_rent_due_sms import build_reminder_message, send_reminder_to_tenant
DOC_CATEGORIES = ["Lease", "ID", "Income", "Notice", "Other"]

st.set_page_config(page_title="Tenants | Propify", page_icon="🏢")
st.title("👤 Tenants")
require_owner_login()
render_company_context()
resp = api_get(f"{API_URL}/tenants/")
leases_r = api_get(f"{API_URL}/leases/")
units_r = api_get(f"{API_URL}/units/")
props_r = api_get(f"{API_URL}/properties/")
payments_r = api_get(f"{API_URL}/payments/")
utility_charges_r = api_get(f"{API_URL}/utility-charges/")

leases = leases_r.json() if leases_r.ok else []
units = {u["id"]: u for u in (units_r.json() if units_r.ok else [])}
properties = {p["id"]: p for p in (props_r.json() if props_r.ok else [])}
payments = payments_r.json() if payments_r.ok else []
utility_charges = utility_charges_r.json() if utility_charges_r.ok else []

leases_by_tenant = defaultdict(list)
for lease in leases:
    leases_by_tenant[lease["tenant_id"]].append(lease)

lease_by_id = {lease["id"]: lease for lease in leases}
payments_by_lease = defaultdict(list)
for payment in payments:
    payments_by_lease[payment["lease_id"]].append(payment)


def parse_uploaded_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_date_value(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def is_lease_active_for_day(lease: dict, current_day: date) -> bool:
    if lease.get("status") != "active":
        return False
    start = parse_date_value(lease.get("start_date"))
    end = parse_date_value(lease.get("end_date"))
    if not start or start > current_day:
        return False
    if end and end < current_day:
        return False
    return True


def monthly_paid_amount(lease_id: int, current_day: date) -> float:
    total = 0.0
    for payment in payments_by_lease.get(lease_id, []):
        payment_day = parse_date_value(payment.get("date"))
        if not payment_day:
            continue
        if payment_day.year == current_day.year and payment_day.month == current_day.month:
            total += float(payment.get("amount", 0) or 0)
    return total


def property_fee_settings(unit: dict | None) -> tuple[int, float]:
    if not unit:
        return 3, 30.0
    prop = properties.get(unit.get("property_id"), {})
    grace_days = int(prop.get("grace_period_days", 3) or 3)
    late_fee_amount = float(prop.get("late_fee_amount", 30) or 30)
    return grace_days, late_fee_amount


def utility_due_for_lease(lease_id: int) -> float:
    return sum(
        float(charge.get("amount", 0) or 0)
        for charge in utility_charges
        if charge.get("lease_id") == lease_id and not charge.get("is_paid", False)
    )

st.subheader("Existing Tenants")
if resp.status_code == 200:
    tenants = resp.json()
    if tenants:
        for t in tenants:
            tenant_leases = leases_by_tenant.get(t["id"], [])
            today = date.today()
            active_leases = [lease for lease in tenant_leases if is_lease_active_for_day(lease, today)]
            rent_due = 0.0
            total_paid = 0.0
            late_fee = 0.0
            utility_due = 0.0
            for lease in active_leases:
                unit = units.get(lease["unit_id"], {})
                monthly_rent = float(unit.get("rent_amount", 0) or 0)
                paid_this_month = monthly_paid_amount(lease["id"], today)
                total_paid += paid_this_month
                remaining_due = max(monthly_rent - paid_this_month, 0.0)
                rent_due += remaining_due
                utility_due += utility_due_for_lease(lease["id"])

                grace_days, property_late_fee = property_fee_settings(unit)
                if today.day > grace_days and remaining_due > 0:
                    late_fee += property_late_fee

            total_due = rent_due + late_fee + utility_due
            cols = st.columns([5, 1])
            cols[0].write(
                f"**{t.get('name', '')}**  \n"
                f"Email: {t.get('email', '') or 'N/A'}  \n"
                f"Phone: {t.get('phone', '') or 'N/A'}  \n"
                f"ID: {t['id']}  \n"
                f"Leases: {len(tenant_leases)}"
            )
            if cols[1].button("Delete", key=f"del-tenant-{t['id']}"):
                dr = api_delete(f"{API_URL}/tenants/{t['id']}")
                if dr.status_code in (200, 204):
                    st.success("Tenant deleted")
                    st.rerun()
                else:
                    st.error(f"Delete failed: {dr.status_code} {dr.text}")

            reminder_col1, reminder_col2 = st.columns([3, 2])
            with reminder_col1:
                preview_message = build_reminder_message(t, total_due, late_fee)
                st.caption(f"Reminder preview: {preview_message}")
            with reminder_col2:
                if st.button("Send Reminder Now", key=f"send-reminder-{t['id']}"):
                    try:
                        result = send_reminder_to_tenant(t["id"])
                        st.success(result)
                    except Exception as exc:
                        st.warning(f"Reminder not sent: {exc}")

            status_col1, status_col2, status_col3, status_col4 = st.columns(4)
            status_col1.metric("Rent Due", f"${rent_due:,.2f}")
            status_col2.metric("Paid This Month", f"${total_paid:,.2f}")
            status_col3.metric("Utility Due", f"${utility_due:,.2f}")
            status_col4.metric("Total Due", f"${total_due:,.2f}")

            if total_due > 0:
                st.markdown(
                    f"<div style='color:#b42318;font-weight:700;'>Amount due now: ${total_due:,.2f}</div>",
                    unsafe_allow_html=True,
                )

            if late_fee > 0:
                st.markdown(
                    f"<div style='color:#b42318;font-weight:700;'>Late fee applied: ${late_fee:,.2f}. Current balance due: ${total_due:,.2f}</div>",
                    unsafe_allow_html=True,
                )
            elif rent_due > 0:
                st.info(f"Rent is due on the 1st of the month. Current balance due: ${total_due:,.2f}")
            else:
                st.success("Current month rent is paid.")

            with st.expander(f"Documents And Leases - {t.get('name', '')}"):
                if tenant_leases:
                    st.markdown("**Lease History**")
                    lease_attach_options = {"No lease-specific link": None}
                    for lease in tenant_leases:
                        unit = units.get(lease["unit_id"])
                        prop = properties.get(unit["property_id"], {}) if unit else {}
                        lease_label = (
                            f"Lease {lease.get('lease_number', lease['id'])} | "
                            f"{prop.get('name', 'Unknown')} | "
                            f"Unit #{unit.get('unit_number', lease['unit_id']) if unit else lease['unit_id']} | "
                            f"{lease.get('start_date')} -> {lease.get('end_date') or 'Open'}"
                        )
                        lease_attach_options[lease_label] = lease["id"]
                        st.write(lease_label)
                        lease_utility_charges = [
                            c for c in utility_charges if c.get("lease_id") == lease["id"]
                        ]
                        if lease_utility_charges:
                            st.caption("Utility charges for this lease:")
                            for charge in sorted(lease_utility_charges, key=lambda c: c.get("bill_date", ""), reverse=True):
                                st.caption(
                                    f"{str(charge.get('utility_type', 'other')).title()} | "
                                    f"${float(charge.get('amount', 0) or 0):,.2f} | "
                                    f"Bill: {charge.get('bill_date')} | Due: {charge.get('due_date') or 'N/A'} | "
                                    f"Status: {'Paid' if charge.get('is_paid') else 'Unpaid'}"
                                )
                else:
                    st.caption("No leases yet for this tenant.")
                    lease_attach_options = {"No lease-specific link": None}

                tenant_docs_r = api_get(f"{API_URL}/documents/tenant/{t['id']}")
                tenant_docs = tenant_docs_r.json() if tenant_docs_r.ok else []

                st.markdown("**Upload Document**")
                upload_col1, upload_col2, upload_col3 = st.columns([2, 1, 2])
                tenant_upload_file = upload_col1.file_uploader(
                    "Choose File",
                    key=f"tenant-upload-file-{t['id']}",
                )
                tenant_doc_type = upload_col2.selectbox(
                    "Category",
                    DOC_CATEGORIES,
                    index=1,
                    key=f"tenant-upload-category-{t['id']}",
                )
                selected_lease_attach = upload_col3.selectbox(
                    "Attach To Lease (optional)",
                    list(lease_attach_options.keys()),
                    key=f"tenant-upload-lease-{t['id']}",
                )

                if st.button("Upload Document", key=f"tenant-upload-submit-{t['id']}"):
                    if not tenant_upload_file:
                        st.warning("Select a file to upload.")
                    else:
                        files = {
                            "file": (
                                tenant_upload_file.name,
                                tenant_upload_file.getvalue(),
                                tenant_upload_file.type or "application/octet-stream",
                            )
                        }
                        data = {
                            "tenant_id": str(t["id"]),
                            "document_type": tenant_doc_type.lower(),
                        }
                        selected_lease_id = lease_attach_options[selected_lease_attach]
                        if selected_lease_id is not None:
                            data["lease_id"] = str(selected_lease_id)

                        ur = api_post(f"{API_URL}/documents/upload", files=files, data=data)
                        if ur.status_code in (200, 201):
                            st.success("Document uploaded")
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {ur.status_code} {ur.text}")

                st.markdown("**Stored Documents**")
                if tenant_docs:
                    category_filter = st.selectbox(
                        "Category Filter",
                        ["All", *DOC_CATEGORIES],
                        index=0,
                        key=f"tenant-doc-filter-{t['id']}",
                    )

                    filtered_docs = []
                    for d in tenant_docs:
                        doc_category = (d.get("document_type") or "other").lower()
                        if category_filter != "All" and doc_category != category_filter.lower():
                            continue

                        uploaded_on = parse_uploaded_date(d.get("uploaded_at"))
                        lease = lease_by_id.get(d.get("lease_id")) if d.get("lease_id") else None
                        unit = units.get(lease["unit_id"]) if lease else None
                        prop = properties.get(unit["property_id"], {}) if unit else {}

                        filtered_docs.append(
                            {
                                "Uploaded": uploaded_on.isoformat() if uploaded_on else "Unknown",
                                "File": d.get("original_filename", ""),
                                "Category": doc_category.title(),
                                "Lease": lease.get("lease_number", "N/A") if lease else "N/A",
                                "Dates": (
                                    f"{lease.get('start_date')} -> {lease.get('end_date') or 'Open'}"
                                    if lease else "N/A"
                                ),
                                "Property": prop.get("name", "N/A") if lease else "N/A",
                                "Unit": f"#{unit.get('unit_number')}" if unit else "N/A",
                                "Download": f"{API_URL}/documents/{d['id']}/download",
                            }
                        )

                    if filtered_docs:
                        st.dataframe(filtered_docs, use_container_width=True)
                    else:
                        st.caption("No documents found for this tenant using current filter.")

                    for d in tenant_docs:
                        action_col1, action_col2 = st.columns([4, 1])
                        with action_col1:
                            download_url = f"{API_URL}/documents/{d['id']}/download"
                            st.markdown(f"[{d['original_filename']}]({download_url})")
                        with action_col2:
                            if st.button("Delete", key=f"tenant-doc-delete-{d['id']}"):
                                dr = api_delete(f"{API_URL}/documents/{d['id']}")
                                if dr.status_code in (200, 204):
                                    st.success("Document deleted")
                                    st.rerun()
                                else:
                                    st.error(f"Delete failed: {dr.status_code} {dr.text}")
                else:
                    st.caption("No documents uploaded yet.")

            st.divider()
    else:
        st.write("No tenants yet.")
else:
    st.error(f"Failed to load tenants: {resp.status_code} {resp.text}")

st.info("Add or invite tenants from Tenant Portal.")
