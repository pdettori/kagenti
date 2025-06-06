# ui/pages/02_Tool_Catalog.py

import streamlit as st
from lib.kube import get_custom_objects_api, list_tools, get_tool_details, get_kube_api_client_cached # Ensure get_custom_objects_api is used
from lib.common_ui import render_resource_catalog
from lib.tool_details_page import render_mcp_tool_details_content 
from lib import constants
import kubernetes # For ApiClient type hint


# --- Main Tool Catalog Page Rendering ---
# Get the CustomObjectsApi (for listing/getting tools)
custom_obj_api = get_custom_objects_api() # Correct function to get CustomObjectsApi
# Get the generic ApiClient (for listing namespaces - returned by the cached function)
generic_api_client, _, _ = get_kube_api_client_cached()


render_resource_catalog(
    st_object=st,
    resource_type_name="Tool",
    list_resources_func=list_tools,
    get_details_func=get_tool_details,
    render_details_func=render_mcp_tool_details_content, 
    custom_obj_api=custom_obj_api, # Pass the CustomObjectsApi
    generic_api_client=generic_api_client, # Pass the generic ApiClient
    session_state_key_selected_resource="selected_tool_name"
)
