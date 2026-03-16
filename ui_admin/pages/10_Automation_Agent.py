from datetime import date

import streamlit as st

from ui_admin.api_client import api_get, api_post
from ui_admin.auth_guard import render_company_context, require_owner_login
from ui_admin.config import API_URL

st.set_page_config(page_title="Automation Agent | Propify", page_icon="🤖")
st.title("🤖 Automation Agent")
require_owner_login()
render_company_context()

st.caption("Run proactive rental workflows. Start with rent reminder previews and one-click execution.")

twilio_status_response = api_get(f"{API_URL}/owner/twilio-status")
twilio_configured = False
if twilio_status_response.ok:
    twilio_configured = bool(twilio_status_response.json().get("configured"))

if not twilio_configured:
    st.warning("Twilio not configured, SMS not sent.")


def _load_preview():
    return api_get(f"{API_URL}/automation/rent-reminders/preview", timeout=15)


preview_response = _load_preview()
if not preview_response.ok:
    st.error(f"Failed to load automation preview: {preview_response.status_code} {preview_response.text}")
    st.stop()

preview = preview_response.json()
items = preview.get("items", [])

m1, m2, m3 = st.columns(3)
m1.metric("Tenants Considered", int(preview.get("total_candidates", 0)))
m2.metric("With Balance Due", int(preview.get("total_with_due", 0)))
m3.metric("Ready To Send", int(preview.get("total_ready_to_send", 0)))

st.caption(f"Computed on {preview.get('run_date', date.today().isoformat())}")

controls_col1, controls_col2, controls_col3 = st.columns([1.2, 1.2, 2.2])
max_messages = controls_col1.number_input(
    "Max Messages",
    min_value=1,
    max_value=500,
    value=min(max(len(items), 1), 100),
    step=1,
)

dry_run_clicked = controls_col2.button("Run Dry-Run", use_container_width=True)
allow_send = controls_col3.checkbox("I confirm: send real SMS reminders now", value=False)

send_clicked = st.button("Send SMS Now", type="primary", disabled=not allow_send)

if dry_run_clicked:
    payload = {"dry_run": True, "max_messages": int(max_messages)}
    run_resp = api_post(f"{API_URL}/automation/rent-reminders/run", json=payload, timeout=30)
    if run_resp.ok:
        run_data = run_resp.json()
        st.success(
            f"Dry-run completed. Evaluated {run_data['considered']} candidates, queued {run_data['queued']} actions."
        )
        if run_data.get("details"):
            st.code("\n".join(run_data["details"]), language="text")
    else:
        st.error(f"Dry-run failed: {run_resp.status_code} {run_resp.text}")

if send_clicked:
    payload = {"dry_run": False, "max_messages": int(max_messages)}
    run_resp = api_post(f"{API_URL}/automation/rent-reminders/run", json=payload, timeout=40)
    if run_resp.ok:
        run_data = run_resp.json()
        st.success(
            f"Automation run complete. Sent {run_data['sent']}, skipped {run_data['skipped_no_phone']}, failures {run_data['failures']}."
        )
        if run_data.get("details"):
            st.code("\n".join(run_data["details"]), language="text")
    else:
        st.error(f"Send failed: {run_resp.status_code} {run_resp.text}")

st.subheader("Rent Reminder Candidates")
if not items:
    st.info("No rent reminders are currently due.")
    st.stop()

rows = []
for item in items:
    rows.append(
        {
            "Tenant": item.get("tenant_name"),
            "Phone": item.get("tenant_phone") or "(missing)",
            "Leases": item.get("lease_count"),
            "Rent Due": f"${float(item.get('rent_due', 0) or 0):,.2f}",
            "Late Fee": f"${float(item.get('late_fee', 0) or 0):,.2f}",
            "Total Due": f"${float(item.get('total_due', 0) or 0):,.2f}",
            "Message": item.get("message"),
        }
    )

st.dataframe(rows, use_container_width=True, hide_index=True)
