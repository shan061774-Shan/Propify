from datetime import date

import streamlit as st
from ui_admin.api_client import api_delete, api_get, api_patch, api_post
from ui_admin.auth_guard import render_company_context, require_owner_login
from ui_admin.config import API_URL

st.set_page_config(page_title="Maintenance | Propify", page_icon="🏢")
st.title("🛠️ Maintenance")
require_owner_login()
render_company_context()


def _owner_context() -> tuple[str, str]:
    profile = st.session_state.get("owner_profile")
    if not profile:
        profile_resp = api_get(f"{API_URL}/owner/profile")
        if profile_resp.ok:
            profile = profile_resp.json()
            st.session_state.owner_profile = profile

    profile = profile or {}
    owner_name = (profile.get("owner_name") or "Owner").strip()
    company_name = (profile.get("company_name") or "Propify Property Management").strip()
    return owner_name, company_name


def _status_badge(status: str) -> str:
    normalized = (status or "").lower()
    if normalized == "approved":
        return "<span style='background:#dcfce7;color:#166534;padding:3px 8px;border-radius:999px;font-weight:600;'>APPROVED</span>"
    if normalized == "accepted":
        return "<span style='background:#dbeafe;color:#1d4ed8;padding:3px 8px;border-radius:999px;font-weight:600;'>ACCEPTED</span>"
    return "<span style='background:#fef3c7;color:#92400e;padding:3px 8px;border-radius:999px;font-weight:600;'>INVITED</span>"


def _portal_base_url() -> str:
    try:
        return st.secrets.get("PORTAL_BASE_URL", "http://127.0.0.1:8501")
    except Exception:
        return "http://127.0.0.1:8501"


def get_json(path: str, required: bool = False):
    response = api_get(f"{API_URL}{path}")
    if response.ok:
        return response.json()
    if required:
        st.error(f"Failed to load {path}: {response.status_code}")
        st.stop()
    return []


properties = get_json("/properties/", required=True)
units = get_json("/units/", required=True)
requests_data = get_json("/maintenance/")
contractors = get_json("/contractors/")
tenants = get_json("/tenants/")
leases = get_json("/leases/")

property_by_id = {p["id"]: p for p in properties}
unit_by_id = {u["id"]: u for u in units}
tenant_by_id = {t["id"]: t for t in tenants}
contractor_by_id = {c["id"]: c for c in contractors}

units_by_property: dict[int, list[dict]] = {}
for u in units:
    units_by_property.setdefault(u["property_id"], []).append(u)

tenant_by_unit: dict[int, dict] = {}
for lease in leases:
    if lease.get("status") == "active" and lease.get("tenant_id") in tenant_by_id:
        tenant_by_unit[lease["unit_id"]] = tenant_by_id[lease["tenant_id"]]


def contractor_label(contractor: dict) -> str:
    parts = [contractor.get("name") or "Unnamed"]
    if contractor.get("specialty"):
        parts.append(contractor["specialty"])
    if contractor.get("phone"):
        parts.append(contractor["phone"])
    return " | ".join(parts)


contractor_choices: list[tuple[str, int | None]] = [("Unassigned", None)]
for c in contractors:
    contractor_choices.append((f"{contractor_label(c)} [#{c['id']}]", c["id"]))

choice_labels = [label for label, _ in contractor_choices]
choice_id_by_label = {label: cid for label, cid in contractor_choices}


def media_preview(photo_path: str | None, width: int = 260):
    if not photo_path:
        return
    ext = photo_path.rsplit(".", 1)[-1].lower()
    media_url = f"{API_URL}/{photo_path}"
    if ext in ("jpg", "jpeg", "png", "gif", "webp"):
        st.image(media_url, width=width)
    elif ext in ("mp4", "mov", "avi", "webm"):
        st.video(media_url)


with st.expander("👷 Contractors", expanded=False):
    st.markdown("**Network Invitations**")
    contractor_portal_link = f"{_portal_base_url().rstrip('/')}/Contractor_Portal"
    owner_name, company_name = _owner_context()
    st.markdown("**Contractor Portal Link**")
    st.code(contractor_portal_link)
    st.caption("Use the copy icon on the code block, then share this link with contractors.")

    inv1, inv2 = st.columns([3, 1])
    contractor_invite_phone = inv1.text_input("Invite contractor by phone", placeholder="e.g. +16145550099")
    contractor_phone_for_message = contractor_invite_phone.strip() or "<contractor phone>"
    contractor_message = (
        f"Hello, this is {owner_name} from {company_name}.\n\n"
        "You are invited to join the Propify Contractor Portal for maintenance assignments.\n\n"
        f"Portal: {contractor_portal_link}\n"
        f"Phone to use: {contractor_phone_for_message}\n\n"
        "Steps:\n"
        "1) Open the portal link\n"
        "2) Click Accept Invite\n"
        "3) Enter the same phone number and complete profile details\n"
        "4) After approval, login with that phone number\n"
    )
    st.markdown("**Copy Invite Message**")
    st.code(contractor_message)
    st.caption("Use the copy icon on the message block to copy in one click.")

    if inv2.button("Send Invite", key="contractor-network-invite-btn", use_container_width=True):
        invite_resp = api_post(f"{API_URL}/network/contractors/invite", json={"phone": contractor_invite_phone.strip()})
        if invite_resp.ok:
            st.success("Contractor invitation sent.")
            st.rerun()
        else:
            st.error(f"Invite failed: {invite_resp.status_code} {invite_resp.text}")

    contractor_network_resp = api_get(f"{API_URL}/network/contractors")
    contractor_links = contractor_network_resp.json() if contractor_network_resp.ok else []
    if contractor_links:
        status_counts: dict[str, int] = {}
        for item in contractor_links:
            status_key = str(item.get("status", "invited")).lower()
            status_counts[status_key] = status_counts.get(status_key, 0) + 1

        statuses = sorted(status_counts.keys())
        filter_choice = st.selectbox(
            "Filter by status",
            ["all", *statuses],
            format_func=lambda x: f"ALL ({len(contractor_links)})" if x == "all" else f"{x.upper()} ({status_counts.get(x, 0)})",
            key="contractor-network-status-filter",
        )

        filtered_links = [
            link for link in contractor_links
            if filter_choice == "all" or str(link.get("status", "")).lower() == filter_choice
        ]

        for link in filtered_links:
            status_value = str(link.get("status", "")).lower()
            info = (
                f"Phone: {link.get('phone', '') or 'N/A'} | "
                f"Contractor ID: {link.get('contractor_id') or '-'}"
            )
            cc1, cc2 = st.columns([5, 1])
            cc1.write(info)
            cc1.markdown(_status_badge(str(link.get("status", "invited"))), unsafe_allow_html=True)
            if status_value == "accepted":
                if cc2.button("Approve", key=f"contractor-link-approve-{link['id']}"):
                    approve_resp = api_post(f"{API_URL}/network/contractors/{link['id']}/approve")
                    if approve_resp.ok:
                        st.success("Contractor connection approved.")
                        st.rerun()
                    else:
                        st.error(f"Approve failed: {approve_resp.status_code} {approve_resp.text}")
            elif status_value == "invited":
                cc2.caption("Waiting acceptance")
            st.caption(
                f"Invited: {link.get('invited_at') or '-'} | "
                f"Accepted: {link.get('accepted_at') or '-'} | "
                f"Approved: {link.get('approved_at') or '-'}"
            )
        if not filtered_links:
            st.caption("No invitations match the selected status.")
    else:
        st.caption("No contractor network invitations yet.")

    st.divider()

    if contractors:
        for c in contractors:
            row_a, row_b = st.columns([5, 1])
            details = (
                f"**{c['name']}**"
                + (f" | {c['specialty']}" if c.get("specialty") else "")
                + (f" | {c['phone']}" if c.get("phone") else "")
                + (f" | {c['email']}" if c.get("email") else "")
                + (f"  \n_{c['notes']}_" if c.get("notes") else "")
            )
            row_a.write(details)
            if row_b.button("Delete", key=f"contractor-del-{c['id']}"):
                delete_resp = api_delete(f"{API_URL}/contractors/{c['id']}")
                if delete_resp.status_code in (200, 204):
                    st.success("Contractor deleted")
                    st.rerun()
                else:
                    st.error(f"Delete failed: {delete_resp.status_code} {delete_resp.text}")
    else:
        st.caption("No contractors yet.")

    st.markdown("**Add Contractor**")
    add_c1, add_c2, add_c3 = st.columns([2, 1, 1])
    new_name = add_c1.text_input("Name", key="contractor-new-name")
    new_phone = add_c2.text_input("Phone", key="contractor-new-phone")
    new_email = add_c3.text_input("Email", key="contractor-new-email")
    add_c4, add_c5 = st.columns([1, 2])
    new_specialty = add_c4.text_input("Specialty", key="contractor-new-specialty")
    new_notes = add_c5.text_input("Notes", key="contractor-new-notes")

    if st.button("Add Contractor", key="contractor-add-btn"):
        if not new_name.strip():
            st.warning("Name is required")
        else:
            payload = {
                "name": new_name.strip(),
                "phone": new_phone.strip(),
                "email": new_email.strip(),
                "specialty": new_specialty.strip(),
                "notes": new_notes.strip(),
            }
            create_resp = api_post(f"{API_URL}/contractors/", json=payload)
            if create_resp.status_code in (200, 201):
                st.success("Contractor added")
                st.rerun()
            else:
                st.error(f"Failed: {create_resp.status_code} {create_resp.text}")


pending_requests = [r for r in requests_data if r.get("status") == "pending"]
st.subheader(f"Pending Approval ({len(pending_requests)})")
if not pending_requests:
    st.caption("No pending requests.")

for req in pending_requests:
    unit = unit_by_id.get(req["unit_id"])
    prop = property_by_id.get(unit["property_id"]) if unit else None
    tenant = tenant_by_unit.get(req["unit_id"])

    st.markdown(
        f"**#{req['id']}** | {prop['name'] if prop else 'Unknown Property'} | "
        f"Unit {unit['unit_number'] if unit else req['unit_id']}"
        + (f" | Tenant: {tenant['name']}" if tenant else "")
        + f"  \n{req['description']}"
    )
    media_preview(req.get("photo_path"), width=320)

    p1, p2, p3, p4 = st.columns([1, 1, 2, 1])
    priority = p1.selectbox("Priority", ["low", "medium", "high"], key=f"pending-priority-{req['id']}")
    new_status = p2.selectbox("Set Status", ["open", "in_progress"], key=f"pending-status-{req['id']}")
    assigned_label = p3.selectbox("Assign Contractor", choice_labels, key=f"pending-contractor-{req['id']}")
    if p4.button("Approve", key=f"pending-approve-{req['id']}", use_container_width=True):
        payload = {
            "priority": priority,
            "status": new_status,
            "contractor_id": choice_id_by_label[assigned_label],
        }
        patch_resp = api_patch(f"{API_URL}/maintenance/{req['id']}", json=payload)
        if patch_resp.ok:
            st.success("Request approved")
            st.rerun()
        else:
            st.error(f"Approve failed: {patch_resp.status_code} {patch_resp.text}")

    if st.button("Reject & Delete", key=f"pending-delete-{req['id']}"):
        delete_resp = api_delete(f"{API_URL}/maintenance/{req['id']}")
        if delete_resp.status_code in (200, 204):
            st.info("Request removed")
            st.rerun()
        else:
            st.error(f"Delete failed: {delete_resp.status_code} {delete_resp.text}")
    st.divider()


active_requests = [r for r in requests_data if r.get("status") != "pending"]
st.subheader("Existing Requests")
if not active_requests:
    st.info("No maintenance requests yet.")

for req in active_requests:
    unit = unit_by_id.get(req["unit_id"])
    prop = property_by_id.get(unit["property_id"]) if unit else None
    assigned = contractor_by_id.get(req.get("contractor_id"))

    st.markdown(
        f"**#{req['id']}** | {prop['name'] if prop else 'Unknown Property'} | "
        f"Unit {unit['unit_number'] if unit else req['unit_id']}  \n"
        f"Priority: **{req['priority']}** | Status: **{req['status']}** | "
        f"Contractor: **{assigned.get('name') if assigned else 'Unassigned'}**"
    )
    st.caption(req["description"])
    media_preview(req.get("photo_path"), width=220)

    default_label = "Unassigned"
    if req.get("contractor_id") is not None:
        for label, cid in contractor_choices:
            if cid == req["contractor_id"]:
                default_label = label
                break

    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    status_options = ["open", "in_progress", "closed"]
    current_status = req.get("status", "open")
    status_index = status_options.index(current_status) if current_status in status_options else 0

    edited_status = c1.selectbox("Status", status_options, index=status_index, key=f"active-status-{req['id']}")
    edited_label = c2.selectbox(
        "Assign Contractor",
        choice_labels,
        index=choice_labels.index(default_label),
        key=f"active-contractor-{req['id']}",
    )

    if c3.button("Update", key=f"active-update-{req['id']}"):
        update_payload = {
            "status": edited_status,
            "contractor_id": choice_id_by_label[edited_label],
        }
        if edited_status == "closed":
            update_payload["closed_date"] = date.today().isoformat()
        update_resp = api_patch(f"{API_URL}/maintenance/{req['id']}", json=update_payload)
        if update_resp.ok:
            st.success("Request updated")
            st.rerun()
        else:
            st.error(f"Update failed: {update_resp.status_code} {update_resp.text}")

    if c4.button("Delete", key=f"active-delete-{req['id']}"):
        delete_resp = api_delete(f"{API_URL}/maintenance/{req['id']}")
        if delete_resp.status_code in (200, 204):
            st.rerun()
        else:
            st.error(f"Delete failed: {delete_resp.status_code} {delete_resp.text}")
    st.divider()


st.subheader("Add New Request")
if not properties:
    st.warning("No properties found. Add a property first.")
    st.stop()

property_options = {f"{p['name']} | {p['address']}": p["id"] for p in properties}
selected_property_label = st.selectbox("Property", list(property_options.keys()), key="admin-new-property")
selected_property_id = property_options[selected_property_label]

available_units = units_by_property.get(selected_property_id, [])
if not available_units:
    st.warning("No units under this property.")
    st.stop()

unit_options = {f"Unit {u['unit_number']}": u["id"] for u in available_units}
selected_unit_label = st.selectbox("Unit", list(unit_options.keys()), key="admin-new-unit")

new_description = st.text_area("Description", key="admin-new-description")
n1, n2, n3 = st.columns([1, 1, 2])
new_priority = n1.selectbox("Priority", ["low", "medium", "high"], key="admin-new-priority")
new_status = n2.selectbox("Status", ["open", "in_progress", "closed"], key="admin-new-status")
new_contractor_label = n3.selectbox("Assign Contractor", choice_labels, key="admin-new-contractor")

new_media_file = st.file_uploader(
    "Attach photo/video (optional)",
    type=["jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "avi", "webm"],
    key="admin-new-media",
)

if st.button("Create Request", key="admin-create-request"):
    if not new_description.strip():
        st.warning("Description is required")
    else:
        media_path = None
        if new_media_file:
            upload_resp = api_post(
                f"{API_URL}/maintenance/upload-photo",
                files={"file": (new_media_file.name, new_media_file.getvalue(), new_media_file.type)},
            )
            if upload_resp.ok:
                media_path = upload_resp.json().get("photo_path")
            else:
                st.warning(f"Upload failed ({upload_resp.status_code}), request will be created without media.")

        payload = {
            "unit_id": unit_options[selected_unit_label],
            "description": new_description.strip(),
            "priority": new_priority,
            "status": new_status,
            "contractor_id": choice_id_by_label[new_contractor_label],
            "photo_path": media_path,
            "request_date": date.today().isoformat(),
        }
        create_resp = api_post(f"{API_URL}/maintenance/", json=payload)
        if create_resp.status_code in (200, 201):
            st.success("Maintenance request created")
            st.rerun()
        else:
            st.error(f"Failed to create request: {create_resp.status_code} {create_resp.text}")

