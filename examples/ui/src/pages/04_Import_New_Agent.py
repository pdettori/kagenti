# ui/pages/04_Import_New_Agent.py

import streamlit as st
from lib.build_utils import render_import_form
from lib import constants
from lib.kube import get_kube_api_client_cached # For generic client, message and icon

# --- Define Agent-Specific Settings for the Import Form ---
AGENT_EXAMPLE_SUBFOLDERS = [
    "acp/acp_ollama_researcher",
    "acp/acp_weather_service",
    "a2a/a2a_contact_extractor",
    "a2a/a2a_currency_converter",
]
AGENT_PROTOCOL_OPTIONS = ["acp", "a2a"] 

# Get the generic ApiClient and status details
k8s_api_client, k8s_client_msg, k8s_client_icon = get_kube_api_client_cached()

render_import_form(
    st_object=st,
    resource_type="Agent",
    example_subfolders=AGENT_EXAMPLE_SUBFOLDERS,
    default_protocol="acp", 
    protocol_options=AGENT_PROTOCOL_OPTIONS,
    default_framework="LangGraph",
    k8s_api_client=k8s_api_client, 
    k8s_client_status_msg=k8s_client_msg,
    k8s_client_status_icon=k8s_client_icon
)
