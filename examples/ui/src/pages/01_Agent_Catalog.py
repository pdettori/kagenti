# ui/pages/01_Agent_Catalog.py

import streamlit as st
from lib.kube import get_custom_objects_api, list_agents, get_agent_details, get_kube_api_client_cached # Changed get_kube_api_client to get_custom_objects_api
from lib.agent_details_page import render_agent_details_content
from lib.common_ui import render_resource_catalog
from lib import constants
import kubernetes # For ApiClient type hint

# --- Main Agent Catalog Page Rendering ---
# Get the CustomObjectsApi (for listing/getting agents)
custom_obj_api = get_custom_objects_api() # Use the correct function name
# Get the generic ApiClient (for listing namespaces - returned by the cached function)
generic_api_client, _, _ = get_kube_api_client_cached()


render_resource_catalog(
    st_object=st, 
    resource_type_name="Agent",
    list_resources_func=list_agents, 
    get_details_func=get_agent_details, 
    render_details_func=render_agent_details_content, 
    custom_obj_api=custom_obj_api, # Pass the CustomObjectsApi
    generic_api_client=generic_api_client, # Pass the generic ApiClient
    session_state_key_selected_resource="selected_agent_name" 
)