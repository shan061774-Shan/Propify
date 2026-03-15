import streamlit as st
from ui_admin.api_client import api_get, api_patch, api_post
from ui_admin.config import API_URL

st.set_page_config(page_title="Propify", page_icon="🏢", layout="wide")

COUNTRY_PHONE_OPTIONS = [
    ("United States/Canada (+1)", "+1"),
    ("India (+91)", "+91"),
    ("United Kingdom (+44)", "+44"),
    ("Australia (+61)", "+61"),
    ("United Arab Emirates (+971)", "+971"),
    ("Singapore (+65)", "+65"),
]
COUNTRY_PHONE_LABELS = [label for label, _ in COUNTRY_PHONE_OPTIONS]
COUNTRY_CODE_BY_LABEL = {label: code for label, code in COUNTRY_PHONE_OPTIONS}


def _reset_owner_session_state() -> None:
    # Clear all owner auth/profile state and related portal/admin keys.
    explicit_keys = {
        "owner_authenticated",
        "owner_profile",
        "owner_access_token",
        "force_owner_login",
        "tenant_portal_token",
        "tenant_portal_profile",
        "tenant_lookup_invites",
        "contractor_portal_token",
        "contractor_portal_profile",
        "contractor_lookup_invites",
        "propify_admin_key",
    }
    prefixes = (
        "owner_",
        "login-",
        "setup-",
        "edit-",
        "tenant_portal_",
        "contractor_portal_",
        "propify-",
    )

    for key in list(st.session_state.keys()):
        if key in explicit_keys or key.startswith(prefixes):
            st.session_state.pop(key, None)

    st.session_state["owner_authenticated"] = False
    st.session_state["owner_access_token"] = None
    st.session_state["owner_profile"] = None
    st.session_state["force_owner_login"] = True
    st.session_state["owner_session_refreshed"] = True

    # Defensive cache clear in case stale profile calls are cached in future changes.
    st.cache_data.clear()
    st.cache_resource.clear()

tool_col1, tool_col2 = st.columns([5, 1])
with tool_col2:
    if st.button("Refresh Owner Session", key="home-refresh-owner-session"):
        _reset_owner_session_state()
        st.rerun()


def _auth_headers() -> dict[str, str]:
    token = st.session_state.get("owner_access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _render_branding(width: int = 340) -> None:
    b1, b2, b3 = st.columns([1, 2, 1])
    with b2:
        st.image("ui_admin/static/propify_logo.svg", width=width)
        st.caption("Operations platform for property owners")


def _safe_get(url: str, **kwargs):
    try:
        return api_get(url, timeout=8, **kwargs)
    except Exception:
        return None


def _safe_post(url: str, **kwargs):
    try:
        return api_post(url, timeout=12, **kwargs)
    except Exception:
        return None


def _safe_patch(url: str, **kwargs):
    try:
        return api_patch(url, timeout=12, **kwargs)
    except Exception:
        return None


def _phone_has_space(phone: str) -> bool:
    return any(ch.isspace() for ch in (phone or ""))


def _build_phone(country_label: str, local_number: str) -> str:
    country_code = COUNTRY_CODE_BY_LABEL.get(country_label, "+1")
    local = (local_number or "").strip()
    if not local:
        raise ValueError("Phone number is required.")
    if _phone_has_space(local):
        raise ValueError("Phone number cannot contain spaces.")
    if not local.isdigit():
        raise ValueError("Phone number must contain digits only.")
    return f"{country_code}{local}"


def fetch_owner_status():
    r = _safe_get(f"{API_URL}/owner/status")
    if r is None:
        return {"is_setup": False, "api_error": True}
    if r.ok:
        payload = r.json()
        payload["api_error"] = False
        return payload
    return {"is_setup": False, "api_error": True}


def fetch_owner_profile():
    r = _safe_get(f"{API_URL}/owner/profile", headers=_auth_headers())
    if r is None:
        return None
    if r.ok:
        return r.json()
    return None

if "owner_authenticated" not in st.session_state:
    st.session_state.owner_authenticated = False
if "owner_profile" not in st.session_state:
    st.session_state.owner_profile = None
if "owner_access_token" not in st.session_state:
    st.session_state.owner_access_token = None
if "show_owner_phone_setup" not in st.session_state:
    st.session_state.show_owner_phone_setup = False

if st.session_state.get("force_owner_login"):
    st.session_state.owner_authenticated = False
    st.session_state.owner_access_token = None
    st.session_state.owner_profile = None
    st.session_state.pop("force_owner_login", None)

if st.session_state.pop("owner_session_refreshed", False):
    st.success("Owner session refreshed. Please log in again.")

owner_status = fetch_owner_status()
is_setup = bool(owner_status.get("is_setup"))
api_error = bool(owner_status.get("api_error"))

if api_error:
    st.warning(
        f"Backend API is unreachable at {API_URL}. Start FastAPI server first, then refresh this page."
    )

if st.session_state.owner_authenticated and st.session_state.owner_access_token:
    refreshed_profile = fetch_owner_profile()
    if refreshed_profile:
        st.session_state.owner_profile = refreshed_profile
    else:
        st.session_state.owner_authenticated = False
        st.session_state.owner_access_token = None
        st.session_state.owner_profile = None

if not is_setup:
    _render_branding(width=320)
    st.markdown("## Propify")
    st.subheader("Owner Account Setup")
    st.caption("Create your property owner login and company profile.")

    c1, c2 = st.columns(2)
    setup_country_label = c1.selectbox(
        "Login Phone Country",
        COUNTRY_PHONE_LABELS,
        key="setup-owner-country",
    )
    setup_owner_phone_local = c2.text_input(
        "Login Phone Number",
        key="setup-owner-phone-local",
        placeholder="e.g. 6146238948",
    )
    password = st.text_input("Password", type="password", key="setup-password")

    st.markdown("**Company Information**")
    company_name = st.text_input("Company Name", key="setup-company-name")
    company_address = st.text_input("Company Address", key="setup-company-address")
    company_phone = st.text_input("Company Phone", key="setup-company-phone")

    st.markdown("**Owner Information**")
    owner_name = st.text_input("Owner Name", key="setup-owner-name")
    owner_email = st.text_input("Owner Email", key="setup-owner-email")
    st.caption("Use country selector + local phone digits only (no spaces).")

    if st.button("Create Owner Account", type="primary"):
        if not password.strip() or not company_name.strip() or not owner_name.strip():
            st.warning("Password, Company Name, and Owner Name are required.")
        else:
            try:
                owner_phone = _build_phone(setup_country_label, setup_owner_phone_local)
            except ValueError as exc:
                st.warning(str(exc))
                st.stop()

            payload = {
                "username": None,
                "password": password,
                "company_name": company_name.strip(),
                "company_address": company_address.strip(),
                "company_phone": company_phone.strip(),
                "owner_name": owner_name.strip(),
                "owner_email": owner_email.strip(),
                "owner_phone": owner_phone,
            }
            setup_r = _safe_post(f"{API_URL}/owner/setup", json=payload)
            if setup_r is None:
                st.error(f"Setup failed: API is unreachable at {API_URL}")
            elif setup_r.status_code in (200, 201):
                st.success("Owner account created. Please log in below.")
                st.rerun()
            else:
                st.error(f"Setup failed: {setup_r.status_code} {setup_r.text}")

    st.stop()

if not st.session_state.owner_authenticated:
    _render_branding(width=320)
    st.markdown("## Propify")
    st.subheader("Owner Login")
    p1, p2, p3 = st.columns([1.5, 2, 2])
    login_country_label = p1.selectbox("Country", COUNTRY_PHONE_LABELS, key="login-phone-country")
    login_phone_local = p2.text_input("Phone Number", key="login-phone-local", placeholder="e.g. 6146238948")
    login_password_phone = p3.text_input("Password", type="password", key="login-password-phone")
    st.caption("Phone login only. Select country code and enter digits without spaces.")
    if st.button("Login With Phone", type="primary"):
        try:
            login_phone = _build_phone(login_country_label, login_phone_local)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

        if _phone_has_space(login_phone):
            st.error("Phone cannot contain spaces.")
        else:
            login_r = _safe_post(
                f"{API_URL}/owner/login",
                json={"phone": login_phone, "password": login_password_phone},
            )
            if login_r is None:
                st.error(f"Login failed: API is unreachable at {API_URL}")
            elif login_r.ok:
                login_payload = login_r.json()
                st.session_state.owner_authenticated = True
                st.session_state.owner_access_token = login_payload.get("access_token")
                st.session_state.owner_profile = login_payload.get("owner")
                st.session_state.show_owner_phone_setup = False
                st.rerun()
            else:
                st.error("Invalid phone/password, blocked account, or invalid phone format.")
                st.session_state.show_owner_phone_setup = True

    if st.session_state.get("show_owner_phone_setup"):
        with st.expander("Phone not registered? Set owner login phone", expanded=True):
            s1, s2, s3 = st.columns([1.5, 2, 2])
            setup_country = s1.selectbox("Country", COUNTRY_PHONE_LABELS, key="register-owner-phone-country")
            setup_local_phone = s2.text_input("Phone Number", key="register-owner-phone-local", placeholder="e.g. 6146238948")
            setup_owner_password = s3.text_input("Owner Password", type="password", key="register-owner-phone-password")
            st.caption("Use your current owner password to register/update login phone.")

            if st.button("Register This Phone", key="register-owner-phone-submit"):
                try:
                    register_phone = _build_phone(setup_country, setup_local_phone)
                except ValueError as exc:
                    st.error(str(exc))
                    st.stop()

                register_r = _safe_post(
                    f"{API_URL}/owner/register-phone",
                    json={"phone": register_phone, "password": setup_owner_password},
                )
                if register_r is None:
                    st.error(f"Phone registration failed: API is unreachable at {API_URL}")
                elif register_r.ok:
                    st.success("Owner phone registered. Log in with this phone now.")
                    st.session_state.show_owner_phone_setup = False
                else:
                    st.error("Could not register phone. Check owner password and try again.")

    st.divider()
    with st.expander("Forgot password", expanded=False):
        st.caption("Request a one-time reset token, then set a new password.")

        r1, r2 = st.columns([1.5, 2])
        reset_country_label = r1.selectbox("Country", COUNTRY_PHONE_LABELS, key="owner-reset-country")
        reset_phone_local = r2.text_input("Phone Number", key="owner-reset-phone-local", placeholder="e.g. 6146238948")
        st.caption("Use the same phone as login. No spaces, digits only.")

        if st.button("Send Reset Link", key="owner-send-reset-link"):
            try:
                reset_phone = _build_phone(reset_country_label, reset_phone_local)
            except ValueError as exc:
                st.error(str(exc))
                st.stop()

            if _phone_has_space(reset_phone):
                st.error("Phone cannot contain spaces.")
            else:
                reset_payload = {
                    "phone": reset_phone,
                }
                request_r = _safe_post(f"{API_URL}/owner/password-reset/request", json=reset_payload)
                if request_r is None:
                    st.error(f"Reset request failed: API is unreachable at {API_URL}")
                elif request_r.ok:
                    reset_data = request_r.json()
                    st.success(reset_data.get("message") or "If the account exists, a reset link has been sent.")
                    preview_token = (reset_data.get("reset_token") or "").strip()
                    if preview_token:
                        st.session_state["owner_reset_token_preview"] = preview_token
                else:
                    st.error("Unable to request reset right now. Please try again.")

        preview_token = (st.session_state.get("owner_reset_token_preview") or "").strip()
        if preview_token:
            st.info("Development token (copy into the form below)")
            st.code(preview_token)

        c1, c2 = st.columns(2)
        confirm_token = c1.text_input("Reset Token", key="owner-reset-token")
        confirm_password = c2.text_input("New Password", type="password", key="owner-reset-new-password")

        if st.button("Reset Password", key="owner-reset-confirm"):
            confirm_r = _safe_post(
                f"{API_URL}/owner/password-reset/confirm",
                json={"token": confirm_token.strip(), "new_password": confirm_password},
            )
            if confirm_r is None:
                st.error(f"Password reset failed: API is unreachable at {API_URL}")
            elif confirm_r.ok:
                st.success("Password reset complete. You can now log in with your new password.")
                st.session_state.pop("owner_reset_token_preview", None)
            else:
                st.error("Invalid/expired token or weak password (min 8 characters).")
    st.stop()

current_owner = st.session_state.owner_profile or {}
company_name = (current_owner.get("company_name") or "Propify").strip()
owner_name = (current_owner.get("owner_name") or current_owner.get("username") or "Owner").strip()

hero_left, hero_center, hero_right = st.columns([1, 2, 1])
with hero_center:
    st.markdown(f"## {company_name}")
    st.caption("Operations platform for property owners")

top_c1, top_c2 = st.columns([5, 1])
top_c1.success(f"Logged in as {owner_name}")
if top_c2.button("Logout"):
    st.session_state.owner_authenticated = False
    st.session_state.owner_access_token = None
    st.session_state.owner_profile = None
    st.rerun()

st.subheader("Company Information")
st.info(
    f"**Company:** {current_owner.get('company_name', '')}  \n"
    f"**Address:** {current_owner.get('company_address', '') or '-'}  \n"
    f"**Phone:** {current_owner.get('company_phone', '') or '-'}"
)

st.subheader("Owner Information")
st.info(
    f"**Name:** {current_owner.get('owner_name', '')}  \n"
    f"**Email:** {current_owner.get('owner_email', '') or '-'}  \n"
    f"**Phone:** {current_owner.get('owner_phone', '') or '-'}"
)

with st.expander("Edit Company / Owner Info", expanded=False):
    e1, e2 = st.columns(2)
    edit_company_name = e1.text_input("Company Name", value=current_owner.get("company_name", ""), key="edit-company-name")
    edit_company_address = e2.text_input("Company Address", value=current_owner.get("company_address", ""), key="edit-company-address")
    e3, e4 = st.columns(2)
    edit_company_phone = e3.text_input("Company Phone", value=current_owner.get("company_phone", ""), key="edit-company-phone")
    edit_owner_name = e4.text_input("Owner Name", value=current_owner.get("owner_name", ""), key="edit-owner-name")
    e5, e6 = st.columns(2)
    edit_owner_email = e5.text_input("Owner Email", value=current_owner.get("owner_email", ""), key="edit-owner-email")
    edit_owner_phone = e6.text_input("Owner Phone", value=current_owner.get("owner_phone", ""), key="edit-owner-phone")

    if st.button("Save Profile Changes"):
        update_payload = {
            "company_name": edit_company_name.strip(),
            "company_address": edit_company_address.strip(),
            "company_phone": edit_company_phone.strip(),
            "owner_name": edit_owner_name.strip(),
            "owner_email": edit_owner_email.strip(),
            "owner_phone": edit_owner_phone.strip(),
        }
        update_r = _safe_patch(f"{API_URL}/owner/profile", json=update_payload, headers=_auth_headers())
        if update_r is None:
            st.error(f"Update failed: API is unreachable at {API_URL}")
        elif update_r.ok:
            st.session_state.owner_profile = update_r.json()
            st.success("Profile updated")
            st.rerun()
        else:
            st.error(f"Update failed: {update_r.status_code} {update_r.text}")

st.write("Use the sidebar to navigate between sections.")
