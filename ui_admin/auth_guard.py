import streamlit as st

from ui_admin.api_client import api_get
from ui_admin.config import API_URL


def _clear_owner_auth_state() -> None:
    explicit_keys = {
        "owner_authenticated",
        "owner_profile",
        "owner_access_token",
        "force_owner_login",
        "owner_session_refreshed",
        "owner_actor_name",
        "owner_actor_type",
        "propify_admin_key",
        "tenant_portal_token",
        "tenant_portal_profile",
        "contractor_portal_token",
        "contractor_portal_profile",
    }
    prefixes = ("owner_", "propify-", "tenant_portal_", "contractor_portal_")

    for key in list(st.session_state.keys()):
        if key in explicit_keys or key.startswith(prefixes):
            st.session_state.pop(key, None)

    st.session_state["owner_authenticated"] = False
    st.session_state["owner_access_token"] = None
    st.session_state["owner_profile"] = None
    st.session_state["owner_actor_name"] = None
    st.session_state["owner_actor_type"] = None


def require_owner_login() -> None:
    """Stop page execution unless owner is authenticated in this Streamlit session."""
    if st.session_state.get("force_owner_login"):
        _clear_owner_auth_state()
        st.warning("Owner session was refreshed. Please sign in again from Home.")
        st.stop()

    if not st.session_state.get("owner_authenticated") or not st.session_state.get("owner_access_token"):
        st.warning("Owner login required. Open the Home page and sign in.")
        st.stop()


def get_owner_profile() -> dict:
    profile = st.session_state.get("owner_profile")
    if profile:
        return profile

    response = api_get(f"{API_URL}/owner/profile")
    if response.ok:
        profile = response.json()
        st.session_state.owner_profile = profile
        return profile
    return {}


def render_company_context() -> None:
    profile = get_owner_profile()
    company_name = (profile.get("company_name") or "Propify").strip()
    owner_name = (profile.get("owner_name") or "Owner").strip()
    st.markdown(f"### {company_name}")
    st.caption(f"Signed in as {owner_name}")
