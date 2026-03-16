import streamlit as st

from ui_admin.api_client import api_get, api_post
from ui_admin.auth_guard import render_company_context, require_owner_login
from ui_admin.config import API_URL

st.set_page_config(page_title="Company Admins | Propify", page_icon="🏢")
st.title("👥 Company Admins")
require_owner_login()
render_company_context()

st.caption("Invite additional company admins to log in with their own phone number and password.")

twilio_status_response = api_get(f"{API_URL}/owner/twilio-status")
twilio_configured = False
if twilio_status_response.ok:
    twilio_configured = bool(twilio_status_response.json().get("configured"))

if not twilio_configured:
    st.warning("Twilio not configured, SMS not sent.")

invite_col1, invite_col2 = st.columns([3, 1])
invite_phone = invite_col1.text_input("Invite company admin by phone")
send_invite = invite_col2.button("Send Invite", use_container_width=True)

if send_invite:
    response = api_post(f"{API_URL}/owner/admins/invite", json={"phone": invite_phone.strip()})
    if response.ok:
        st.success("Company admin invited.")
        st.rerun()
    else:
        st.error(f"Invite failed: {response.status_code} {response.text}")

admins_response = api_get(f"{API_URL}/owner/admins")
if not admins_response.ok:
    st.error(f"Failed to load company admins: {admins_response.status_code} {admins_response.text}")
    st.stop()

admins = admins_response.json()
if not admins:
    st.info("No additional company admins invited yet.")
    st.stop()

for admin in admins:
    st.write(
        f"Phone: {admin.get('phone') or '-'} | "
        f"Name: {admin.get('name') or '-'} | "
        f"Email: {admin.get('email') or '-'}"
    )
    st.caption(
        f"Status: {str(admin.get('status', '')).upper()} | "
        f"Invited: {admin.get('invited_at') or '-'} | "
        f"Accepted: {admin.get('accepted_at') or '-'}"
    )
    st.divider()