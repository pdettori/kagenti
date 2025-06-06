# ui/pages/05_Import_New_Tool.py

import streamlit as st
from lib.build_utils import render_import_form
from lib import constants
from lib.kube import get_kube_api_client_cached # For generic client, message and icon

# --- Define Tool-Specific Settings for the Import Form ---
TOOL_EXAMPLE_SUBFOLDERS = [
    "mcp/weather_tool",
]
TOOL_PROTOCOL_OPTIONS = ["MCP", "gRPC", "HTTP"] 

# Get the generic ApiClient and status details
k8s_api_client, k8s_client_msg, k8s_client_icon = get_kube_api_client_cached()

render_import_form(
    st_object=st,
    resource_type="Tool",
    example_subfolders=TOOL_EXAMPLE_SUBFOLDERS,
    default_protocol="MCP", 
    protocol_options=TOOL_PROTOCOL_OPTIONS, 
    default_framework="Python",
    k8s_api_client=k8s_api_client,
    k8s_client_status_msg=k8s_client_msg,
    k8s_client_status_icon=k8s_client_icon
)

st.markdown("---")
st.warning(
    "**Note:** The build process for 'Tools' currently uses the same 'AgentBuild' CRD mechanism. "
    "Ensure your operator and CRDs are configured to handle 'tool' types appropriately."
)
