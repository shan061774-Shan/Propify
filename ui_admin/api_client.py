import requests
import streamlit as st


def _auth_headers() -> dict[str, str]:
    token = st.session_state.get("owner_access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _merge_headers(headers: dict | None) -> dict[str, str]:
    merged = _auth_headers()
    if headers:
        merged.update(headers)
    return merged


def api_get(url: str, **kwargs):
    kwargs["headers"] = _merge_headers(kwargs.get("headers"))
    return requests.get(url, **kwargs)


def api_post(url: str, **kwargs):
    kwargs["headers"] = _merge_headers(kwargs.get("headers"))
    return requests.post(url, **kwargs)


def api_patch(url: str, **kwargs):
    kwargs["headers"] = _merge_headers(kwargs.get("headers"))
    return requests.patch(url, **kwargs)


def api_delete(url: str, **kwargs):
    kwargs["headers"] = _merge_headers(kwargs.get("headers"))
    return requests.delete(url, **kwargs)
