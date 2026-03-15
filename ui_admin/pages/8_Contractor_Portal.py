from ui_admin.api_client import api_get, api_patch, api_post
from ui_admin.config import API_URL
import streamlit as st

st.set_page_config(page_title="Contractor Portal | Propify", page_icon="🏢")
st.title("👷 Contractor Portal")


def contractor_headers() -> dict[str, str]:
    token = st.session_state.get("contractor_portal_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


if "contractor_portal_token" not in st.session_state:
    st.session_state.contractor_portal_token = None

if "contractor_portal_profile" not in st.session_state:
    st.session_state.contractor_portal_profile = None

if not st.session_state.contractor_portal_token:
    login_tab, accept_tab = st.tabs(["Login", "Accept Invite"])

    with login_tab:
        phone_input = st.text_input("Enter your phone number", placeholder="e.g. 6145550099")
        if st.button("Login", type="primary"):
            login_r = api_post(f"{API_URL}/portal/contractor/login", json={"phone": phone_input.strip()})
            if login_r.ok:
                payload = login_r.json()
                st.session_state.contractor_portal_token = payload.get("access_token")
                st.session_state.contractor_portal_profile = payload.get("contractor")
                st.rerun()
            else:
                st.error("No contractor account found with that phone number.")

    with accept_tab:
        lookup_phone = st.text_input("Your phone number", placeholder="e.g. 6145550099", key="contractor-invite-phone")
        invites = []
        if st.button("Find My Invitations", key="contractor-invite-lookup"):
            lookup_r = api_post(
                f"{API_URL}/portal/contractor/invitations/lookup",
                json={"phone": lookup_phone.strip()},
            )
            if lookup_r.ok:
                invites = lookup_r.json()
                st.session_state["contractor_lookup_invites"] = invites
            else:
                st.error(f"Lookup failed: {lookup_r.status_code} {lookup_r.text}")

        invites = st.session_state.get("contractor_lookup_invites", invites)
        if invites:
            invite_options = {
                f"Invite #{item['id']} | owner {item['owner_id']} | {str(item.get('status', '')).upper()}": item
                for item in invites
            }
            selected_label = st.selectbox(
                "Select invitation",
                list(invite_options.keys()),
                key="contractor-invite-select",
            )
            selected_invite = invite_options[selected_label]

            in1, in2, in3 = st.columns(3)
            accept_name = in1.text_input("Full name", key="contractor-invite-name")
            accept_email = in2.text_input("Email", key="contractor-invite-email")
            accept_specialty = in3.text_input("Specialty", key="contractor-invite-specialty")

            if st.button("Accept Invitation", key="contractor-invite-accept", type="primary"):
                accept_r = api_post(
                    f"{API_URL}/portal/contractor/invitations/{selected_invite['id']}/accept",
                    json={
                        "phone": lookup_phone.strip(),
                        "name": accept_name.strip(),
                        "email": accept_email.strip(),
                        "specialty": accept_specialty.strip(),
                    },
                )
                if accept_r.ok:
                    st.success("Invitation accepted. Logging you in...")
                    login_r = api_post(f"{API_URL}/portal/contractor/login", json={"phone": lookup_phone.strip()})
                    if login_r.ok:
                        payload = login_r.json()
                        st.session_state.contractor_portal_token = payload.get("access_token")
                        st.session_state.contractor_portal_profile = payload.get("contractor")
                        st.rerun()
                    else:
                        st.info("Invitation accepted. Use the Login tab to continue.")
                else:
                    st.error(f"Accept failed: {accept_r.status_code} {accept_r.text}")
        else:
            st.caption("No invitations loaded. Use your phone to look up invites.")
    st.stop()

me_r = api_get(f"{API_URL}/portal/contractor/me", headers=contractor_headers())
if not me_r.ok:
    st.session_state.contractor_portal_token = None
    st.session_state.contractor_portal_profile = None
    st.warning("Session expired. Please log in again.")
    st.rerun()

me = me_r.json()
st.session_state.contractor_portal_profile = me

context_r = api_get(f"{API_URL}/portal/contractor/management-context", headers=contractor_headers())
context_payload = context_r.json() if context_r.ok else {"company_names": [], "owner_names": []}
company_names = context_payload.get("company_names", [])
if company_names:
    st.info(f"Managed by {', '.join(company_names)}")

head_col1, head_col2 = st.columns([5, 1])
head_col1.success(f"Welcome, {me.get('name', 'Contractor')}!")
if head_col2.button("Logout"):
    st.session_state.contractor_portal_token = None
    st.session_state.contractor_portal_profile = None
    st.rerun()

with st.expander("📇 My Profile", expanded=False):
    pf1, pf2, pf3 = st.columns(3)
    new_name = pf1.text_input("Full Name", value=me.get("name", ""), key="contractor-prof-name")
    new_phone = pf2.text_input("Phone", value=me.get("phone", ""), key="contractor-prof-phone")
    new_email = pf3.text_input("Email", value=me.get("email", ""), key="contractor-prof-email")
    pf4, pf5 = st.columns([1, 2])
    new_specialty = pf4.text_input("Specialty", value=me.get("specialty", ""), key="contractor-prof-specialty")
    new_notes = pf5.text_input("Notes", value=me.get("notes", ""), key="contractor-prof-notes")
    if st.button("Save Profile", key="contractor-save-profile"):
        update_r = api_patch(
            f"{API_URL}/portal/contractor/me",
            headers=contractor_headers(),
            json={
                "name": new_name.strip(),
                "phone": new_phone.strip(),
                "email": new_email.strip(),
                "specialty": new_specialty.strip(),
                "notes": new_notes.strip(),
            },
        )
        if update_r.ok:
            st.success("Profile updated")
            st.rerun()
        else:
            st.error(f"Update failed: {update_r.status_code} {update_r.text}")

with st.expander("🤝 Owner Invitations", expanded=False):
    my_invites_r = api_get(f"{API_URL}/portal/contractor/invitations", headers=contractor_headers())
    my_invites = my_invites_r.json() if my_invites_r.ok else []
    if my_invites:
        for item in my_invites:
            st.write(
                f"Invite #{item['id']} | Owner {item['owner_id']} | "
                f"Status: {str(item.get('status', '')).upper()}"
            )
            if str(item.get("status", "")).lower() == "invited":
                if st.button("Accept", key=f"contractor-auth-accept-{item['id']}"):
                    accept_r = api_post(
                        f"{API_URL}/portal/contractor/invitations/{item['id']}/accept-auth",
                        headers=contractor_headers(),
                    )
                    if accept_r.ok:
                        st.success("Invitation accepted.")
                        st.rerun()
                    else:
                        st.error(f"Accept failed: {accept_r.status_code} {accept_r.text}")
            st.caption(
                f"Invited: {item.get('invited_at') or '-'} | "
                f"Accepted: {item.get('accepted_at') or '-'} | "
                f"Approved: {item.get('approved_at') or '-'}"
            )
    else:
        st.caption("No invitations found.")

requests_r = api_get(f"{API_URL}/portal/contractor/requests", headers=contractor_headers())
requests_data = requests_r.json() if requests_r.ok else []

active_jobs = [r for r in requests_data if r.get("status") in ("open", "in_progress")]
closed_jobs = [r for r in requests_data if r.get("status") == "closed"]

m1, m2, m3 = st.columns(3)
m1.metric("Total Assigned", len(requests_data))
m2.metric("Active Jobs", len(active_jobs))
m3.metric("Completed", len(closed_jobs))

st.subheader("🔧 Active Jobs")
if active_jobs:
    for req in active_jobs:
        st.write(
            f"#{req['id']} | {req['property_name']} | Unit {req['unit_number']} | "
            f"{req['priority']} | {req['status']}"
        )
        st.caption(req["description"])

        if req.get("photo_path"):
            media_url = f"{API_URL}/{req['photo_path']}"
            ext = req["photo_path"].rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png", "gif", "webp"):
                st.image(media_url, width=280)
            elif ext in ("mp4", "mov", "avi", "webm"):
                st.video(media_url)

        current_status = req.get("status", "open")
        status_options = ["open", "in_progress", "closed"]
        status_idx = status_options.index(current_status) if current_status in status_options else 0
        new_status = st.selectbox("Update Status", status_options, index=status_idx, key=f"ctr-status-{req['id']}")

        if st.button("Save", key=f"ctr-save-{req['id']}"):
            update_r = api_patch(
                f"{API_URL}/portal/contractor/requests/{req['id']}",
                headers=contractor_headers(),
                json={"status": new_status},
            )
            if update_r.ok:
                st.success("Status updated")
                st.rerun()
            else:
                st.error(f"Update failed: {update_r.status_code} {update_r.text}")
        st.divider()
else:
    st.caption("No active jobs assigned right now.")

if closed_jobs:
    with st.expander(f"✅ Completed Jobs ({len(closed_jobs)})", expanded=False):
        for req in closed_jobs:
            st.write(
                f"#{req['id']} | {req['property_name']} | Unit {req['unit_number']} | "
                f"Closed: {req.get('closed_date') or '-'}"
            )
            st.caption(req["description"])
