import os

import streamlit as st


DEFAULT_API_URL = "http://127.0.0.1:8000"

env_api_url = os.getenv("PROPIFY_API_URL")
if env_api_url:
	API_URL = env_api_url
else:
	try:
		API_URL = st.secrets.get("API_URL", DEFAULT_API_URL)
	except Exception:
		API_URL = DEFAULT_API_URL
