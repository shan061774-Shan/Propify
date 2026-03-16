from ui_admin.api_client import api_get, api_patch, api_post
from ui_admin.config import API_URL
import streamlit as st

st.set_page_config(page_title="Tenant Portal | Propify", page_icon="🏢")
st.title("🏠 Tenant Portal")


def tenant_headers() -> dict[str, str]:
    token = st.session_state.get("tenant_portal_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _owner_logged_in() -> bool:
    return bool(st.session_state.get("owner_authenticated") and st.session_state.get("owner_access_token"))


def _phone_has_space(phone: str) -> bool:
    return any(ch.isspace() for ch in phone)


if "tenant_portal_token" not in st.session_state:
    st.session_state.tenant_portal_token = None

if "tenant_portal_profile" not in st.session_state:
    st.session_state.tenant_portal_profile = None

if _owner_logged_in():
    with st.expander("🛠️ Owner Tools: Manage Tenants", expanded=False):
        twilio_status_response = api_get(f"{API_URL}/owner/twilio-status")
        twilio_configured = False
        if twilio_status_response.ok:
            twilio_configured = bool(twilio_status_response.json().get("configured"))
        if not twilio_configured:
            st.warning("Twilio not configured, SMS not sent.")

        tenants_r = api_get(f"{API_URL}/tenants/")
        tenants = tenants_r.json() if tenants_r.ok else []

        st.markdown("**All Tenants**")
        if tenants:
            for tenant in tenants:
                st.write(
                    f"#{tenant['id']} | {tenant.get('name') or '-'} | "
                    f"{tenant.get('phone') or 'N/A'} | {tenant.get('email') or 'N/A'}"
                )
        else:
            st.caption("No tenants found.")

        st.divider()
        st.markdown("**Add Tenant + Send Invite**")
        ot1, ot2, ot3 = st.columns(3)
        owner_tenant_name = ot1.text_input("Name", key="owner-tenant-add-name")
        owner_tenant_email = ot2.text_input("Email", key="owner-tenant-add-email")
        owner_tenant_phone = ot3.text_input("Phone", key="owner-tenant-add-phone")

        if st.button("Add Tenant And Invite", key="owner-tenant-add-invite", use_container_width=True):
            phone = owner_tenant_phone.strip()
            if not owner_tenant_name.strip():
                st.warning("Name is required.")
            elif not phone:
                st.warning("Phone is required.")
            elif _phone_has_space(phone):
                st.warning("Phone cannot contain spaces.")
            else:
                create_r = api_post(
                    f"{API_URL}/tenants/",
                    json={
                        "name": owner_tenant_name.strip(),
                        "email": owner_tenant_email.strip(),
                        "phone": phone,
                    },
                )
                if create_r.status_code not in (200, 201):
                    st.error(f"Create failed: {create_r.status_code} {create_r.text}")
                else:
                    invite_r = api_post(f"{API_URL}/network/tenants/invite", json={"phone": phone})
                    if invite_r.ok:
                        st.success("Tenant added and invite sent.")
                    else:
                        st.warning(f"Tenant added, but invite failed: {invite_r.status_code} {invite_r.text}")
                    st.rerun()

        st.markdown("**Invite Existing Tenant By Phone**")
        invite_phone = st.text_input("Phone Number", key="owner-tenant-invite-phone")
        if st.button("Send Invite", key="owner-tenant-invite-btn"):
            phone = invite_phone.strip()
            if not phone:
                st.warning("Phone is required.")
            elif _phone_has_space(phone):
                st.warning("Phone cannot contain spaces.")
            else:
                invite_r = api_post(f"{API_URL}/network/tenants/invite", json={"phone": phone})
                if invite_r.ok:
                    st.success("Invite sent.")
                    st.rerun()
                else:
                    st.error(f"Invite failed: {invite_r.status_code} {invite_r.text}")

if not st.session_state.tenant_portal_token:
    login_tab, accept_tab = st.tabs(["Login", "Accept Invite"])

    with login_tab:
        phone_input = st.text_input("Enter your phone number", placeholder="e.g. 6145550001")
        if st.button("Login", type="primary"):
            login_r = api_post(f"{API_URL}/portal/tenant/login", json={"phone": phone_input.strip()})
            if login_r.ok:
                payload = login_r.json()
                st.session_state.tenant_portal_token = payload.get("access_token")
                st.session_state.tenant_portal_profile = payload.get("tenant")
                st.rerun()
            else:
                st.error("No tenant account found with that phone number.")

    with accept_tab:
        lookup_phone = st.text_input("Your phone number", placeholder="e.g. 6145550001", key="tenant-invite-phone")
        invites = []
        if st.button("Find My Invitations", key="tenant-invite-lookup"):
            lookup_r = api_post(
                f"{API_URL}/portal/tenant/invitations/lookup",
                json={"phone": lookup_phone.strip()},
            )
            if lookup_r.ok:
                invites = lookup_r.json()
                st.session_state["tenant_lookup_invites"] = invites
            else:
                st.error(f"Lookup failed: {lookup_r.status_code} {lookup_r.text}")

        invites = st.session_state.get("tenant_lookup_invites", invites)
        if invites:
            invite_options = {
                f"Invite #{item['id']} | owner {item['owner_id']} | {str(item.get('status', '')).upper()}": item
                for item in invites
            }
            selected_label = st.selectbox("Select invitation", list(invite_options.keys()), key="tenant-invite-select")
            selected_invite = invite_options[selected_label]

            in1, in2 = st.columns(2)
            accept_name = in1.text_input("Full name", key="tenant-invite-name")
            accept_email = in2.text_input("Email", key="tenant-invite-email")

            if st.button("Accept Invitation", key="tenant-invite-accept", type="primary"):
                accept_r = api_post(
                    f"{API_URL}/portal/tenant/invitations/{selected_invite['id']}/accept",
                    json={
                        "phone": lookup_phone.strip(),
                        "name": accept_name.strip(),
                        "email": accept_email.strip(),
                    },
                )
                if accept_r.ok:
                    st.success("Invitation accepted. Logging you in...")
                    login_r = api_post(f"{API_URL}/portal/tenant/login", json={"phone": lookup_phone.strip()})
                    if login_r.ok:
                        payload = login_r.json()
                        st.session_state.tenant_portal_token = payload.get("access_token")
                        st.session_state.tenant_portal_profile = payload.get("tenant")
                        st.rerun()
                    else:
                        st.info("Invitation accepted. Use the Login tab to continue.")
                else:
                    st.error(f"Accept failed: {accept_r.status_code} {accept_r.text}")
        else:
            st.caption("No invitations loaded. Use your phone to look up invites.")
    st.stop()

profile_r = api_get(f"{API_URL}/portal/tenant/me", headers=tenant_headers())
if not profile_r.ok:
    st.session_state.tenant_portal_token = None
    st.session_state.tenant_portal_profile = None
    st.warning("Session expired. Please log in again.")
    st.rerun()

me = profile_r.json()
st.session_state.tenant_portal_profile = me

context_r = api_get(f"{API_URL}/portal/tenant/management-context", headers=tenant_headers())
context_payload = context_r.json() if context_r.ok else {"company_names": [], "owner_names": []}
company_names = context_payload.get("company_names", [])
if company_names:
    st.info(f"Managed by {', '.join(company_names)}")

head_col1, head_col2 = st.columns([5, 1])
head_col1.success(f"Welcome, {me.get('name', 'Tenant')}!")
if head_col2.button("Logout"):
    st.session_state.tenant_portal_token = None
    st.session_state.tenant_portal_profile = None
    st.rerun()

with st.expander("👤 My Profile", expanded=False):
    pf1, pf2, pf3 = st.columns(3)
    new_name = pf1.text_input("Full Name", value=me.get("name", ""), key="tenant-prof-name")
    new_email = pf2.text_input("Email", value=me.get("email", ""), key="tenant-prof-email")
    new_phone = pf3.text_input("Phone", value=me.get("phone", ""), key="tenant-prof-phone")
    if st.button("Save Profile", key="tenant-save-profile"):
        update_r = api_patch(
            f"{API_URL}/portal/tenant/me",
            json={"name": new_name.strip(), "email": new_email.strip(), "phone": new_phone.strip()},
            headers=tenant_headers(),
        )
        if update_r.ok:
            st.success("Profile updated")
            st.rerun()
        else:
            st.error(f"Update failed: {update_r.status_code} {update_r.text}")

with st.expander("🤝 Owner Invitations", expanded=False):
    my_invites_r = api_get(f"{API_URL}/portal/tenant/invitations", headers=tenant_headers())
    my_invites = my_invites_r.json() if my_invites_r.ok else []
    if my_invites:
        for item in my_invites:
            st.write(
                f"Invite #{item['id']} | Owner {item['owner_id']} | "
                f"Status: {str(item.get('status', '')).upper()}"
            )
            if str(item.get("status", "")).lower() == "invited":
                if st.button("Accept", key=f"tenant-auth-accept-{item['id']}"):
                    accept_r = api_post(
                        f"{API_URL}/portal/tenant/invitations/{item['id']}/accept-auth",
                        headers=tenant_headers(),
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

leases_r = api_get(f"{API_URL}/portal/tenant/leases", headers=tenant_headers())
leases = leases_r.json() if leases_r.ok else []

if not leases:
    st.info("You do not have an active lease. Contact your property manager.")
    st.stop()

unit_choices = {
    f"{row['property_name']} | Unit {row['unit_number']} ({row['property_address']})": row["unit_id"] for row in leases
}
selected_label = st.selectbox("Select Unit", list(unit_choices.keys()))
selected_unit_id = unit_choices[selected_label]

with st.expander("📄 My Documents", expanded=False):
    docs_r = api_get(f"{API_URL}/portal/tenant/documents", headers=tenant_headers())
    docs = docs_r.json() if docs_r.ok else []
    if docs:
        for doc in docs:
            st.write(f"📎 {doc['original_filename']} ({doc.get('document_type', 'other')})")
            download_r = api_get(
                f"{API_URL}/portal/tenant/documents/{doc['id']}/download",
                headers=tenant_headers(),
            )
            if download_r.ok:
                st.download_button(
                    label=f"Download {doc['original_filename']}",
                    data=download_r.content,
                    file_name=doc["original_filename"],
                    key=f"tenant-doc-download-{doc['id']}",
                )
    else:
        st.caption("No documents uploaded yet.")

    doc_type = st.selectbox("Document Type", ["id", "income_proof", "insurance", "other"], key="tenant-doc-type")
    doc_file = st.file_uploader("Upload Document", key="tenant-doc-upload")
    if doc_file and st.button("Upload Document", key="tenant-doc-upload-btn"):
        upload_r = api_post(
            f"{API_URL}/portal/tenant/documents/upload",
            headers=tenant_headers(),
            data={"document_type": doc_type},
            files={"file": (doc_file.name, doc_file.getvalue(), doc_file.type or "application/octet-stream")},
        )
        if upload_r.status_code in (200, 201):
            st.success("Document uploaded")
            st.rerun()
        else:
            st.error(f"Upload failed: {upload_r.status_code} {upload_r.text}")

requests_r = api_get(f"{API_URL}/portal/tenant/requests", headers=tenant_headers())
requests_data = requests_r.json() if requests_r.ok else []

st.subheader("📋 My Requests")
if requests_data:
    for req in requests_data:
        st.write(
            f"#{req['id']} | {req['property_name']} | Unit {req['unit_number']} | "
            f"{req['status']} | {req['description']}"
        )
        if req.get("photo_path"):
            media_url = f"{API_URL}/{req['photo_path']}"
            ext = req["photo_path"].rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png", "gif", "webp"):
                st.image(media_url, width=260)
            elif ext in ("mp4", "mov", "avi", "webm"):
                st.video(media_url)
        st.divider()
else:
    st.caption("No requests submitted yet.")

st.subheader("📝 New Maintenance Request")
description = st.text_area("Describe the issue")
priority = st.selectbox("Priority", ["low", "medium", "high"], index=0)
media_file = st.file_uploader(
    "Attach photo/video (optional)",
    type=["jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "avi", "webm"],
    key="tenant-req-media",
)

if st.button("Submit Request", type="primary", use_container_width=True):
    if not description.strip():
        st.warning("Description is required.")
    else:
        photo_path = None
        if media_file:
            upload_media_r = api_post(
                f"{API_URL}/portal/tenant/upload-photo",
                headers=tenant_headers(),
                files={"file": (media_file.name, media_file.getvalue(), media_file.type or "application/octet-stream")},
            )
            if upload_media_r.ok:
                photo_path = upload_media_r.json().get("photo_path")
            else:
                st.warning(f"Media upload failed ({upload_media_r.status_code}). Submitting without media.")

        create_r = api_post(
            f"{API_URL}/portal/tenant/requests",
            headers=tenant_headers(),
            json={
                "unit_id": selected_unit_id,
                "description": description.strip(),
                "priority": priority,
                "photo_path": photo_path,
            },
        )
        if create_r.status_code in (200, 201):
            st.success("Request submitted. Your property manager will review it soon.")
            st.rerun()
        else:
            st.error(f"Submission failed: {create_r.status_code} {create_r.text}")
