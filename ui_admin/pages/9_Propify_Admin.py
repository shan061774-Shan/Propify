import streamlit as st

from ui_admin.api_client import api_post
from ui_admin.auth_guard import render_company_context, require_owner_login
from ui_admin.config import API_URL

st.set_page_config(page_title="Propify Admin | Propify", page_icon="🏢")


def _reset_owner_session_state() -> None:
    keys_to_clear = {
        "owner_authenticated",
        "owner_profile",
        "owner_access_token",
        "force_owner_login",
        "propify_admin_key",
        "tenant_portal_token",
        "tenant_portal_profile",
        "contractor_portal_token",
        "contractor_portal_profile",
    }
    prefixes = ("owner_", "propify-", "tenant_portal_", "contractor_portal_")

    for key in list(st.session_state.keys()):
        if key in keys_to_clear or key.startswith(prefixes):
            st.session_state.pop(key, None)

    st.session_state["owner_authenticated"] = False
    st.session_state["owner_access_token"] = None
    st.session_state["owner_profile"] = None
    st.session_state["force_owner_login"] = True
    st.session_state["owner_session_refreshed"] = True

    st.cache_data.clear()
    st.cache_resource.clear()


st.title("🛡️ Propify Admin")
require_owner_login()
render_company_context()

toolbar_left, toolbar_mid, toolbar_right = st.columns([4, 1.2, 1.2])
with toolbar_mid:
    if st.button("Refresh Page", key="propify-admin-refresh-page", use_container_width=True):
        st.rerun()
with toolbar_right:
    if st.button("Refresh Owner Session", key="propify-admin-refresh-owner", use_container_width=True):
        _reset_owner_session_state()
        st.rerun()

st.warning("Restricted operations page. Use for emergency owner access control only.")


def _has_space(value: str) -> bool:
    return any(ch.isspace() for ch in (value or ""))


with st.expander("Owner Block / Unblock by Phone", expanded=True):
    st.caption("Phone must match owner login phone exactly. Use digits with optional leading + and no spaces.")

    admin_key = st.text_input(
        "Propify Admin Key",
        type="password",
        value=st.session_state.get("propify_admin_key", ""),
        key="propify-admin-key-input",
    )
    st.session_state["propify_admin_key"] = admin_key

    c1, c2 = st.columns(2)
    owner_phone = c1.text_input("Owner Phone", placeholder="e.g. +16145550099", key="propify-owner-phone")
    block_reason = c2.text_input("Block Reason", value="Compliance hold", key="propify-block-reason")

    b1, b2 = st.columns(2)

    if st.button("Check Status", key="propify-owner-check-status", use_container_width=True):
        if not admin_key.strip():
            st.error("Propify Admin Key is required.")
        elif not owner_phone.strip():
            st.error("Owner phone is required.")
        elif _has_space(owner_phone):
            st.error("Owner phone cannot contain spaces.")
        else:
            status_response = api_post(
                f"{API_URL}/owner/ops/status-by-phone",
                headers={"X-Propify-Admin-Key": admin_key.strip()},
                json={"phone": owner_phone.strip()},
                timeout=12,
            )
            if status_response.ok:
                data = status_response.json()
                if not data.get("found"):
                    st.warning(f"No owner found for phone {owner_phone.strip()}.")
                else:
                    blocked = bool(data.get("is_blocked"))
                    if blocked:
                        st.error("Status: BLOCKED")
                    else:
                        st.success("Status: ACTIVE")
                    st.caption(
                        f"Phone: {data.get('phone')} | Username: {data.get('username') or '-'} | Reason: {data.get('blocked_reason') or '-'}"
                    )
            else:
                st.error(f"Status check failed: {status_response.status_code} {status_response.text}")

    if b1.button("Block Owner", type="primary", use_container_width=True):
        if not admin_key.strip():
            st.error("Propify Admin Key is required.")
        elif not owner_phone.strip():
            st.error("Owner phone is required.")
        elif _has_space(owner_phone):
            st.error("Owner phone cannot contain spaces.")
        else:
            response = api_post(
                f"{API_URL}/owner/ops/block-by-phone",
                headers={"X-Propify-Admin-Key": admin_key.strip()},
                json={"phone": owner_phone.strip(), "reason": block_reason.strip() or None},
                timeout=12,
            )
            if response.ok:
                st.success("Owner account blocked successfully.")
            else:
                st.error(f"Block failed: {response.status_code} {response.text}")

    if b2.button("Unblock Owner", use_container_width=True):
        if not admin_key.strip():
            st.error("Propify Admin Key is required.")
        elif not owner_phone.strip():
            st.error("Owner phone is required.")
        elif _has_space(owner_phone):
            st.error("Owner phone cannot contain spaces.")
        else:
            response = api_post(
                f"{API_URL}/owner/ops/unblock-by-phone",
                headers={"X-Propify-Admin-Key": admin_key.strip()},
                json={"phone": owner_phone.strip()},
                timeout=12,
            )
            if response.ok:
                st.success("Owner account unblocked successfully.")
            else:
                st.error(f"Unblock failed: {response.status_code} {response.text}")

st.info("Tip: Set backend env var PROPIFY_ADMIN_KEY to enable these operations.")
