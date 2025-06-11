# Copyright 2025 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import streamlit as st
from lib.kube import (
    get_custom_objects_api,
    list_agents,
    get_agent_details,
    get_kube_api_client_cached,
)
from lib.agent_details_page import render_agent_details_content
from lib.common_ui import render_resource_catalog
from lib import constants
import kubernetes 

# --- Main Agent Catalog Page Rendering ---

# Get the CustomObjectsApi (for listing/getting agents)
custom_obj_api = get_custom_objects_api()  # Use the correct function name
# Get the generic ApiClient (for listing namespaces - returned by the cached function)
generic_api_client, _, _ = get_kube_api_client_cached()


render_resource_catalog(
    st_object=st,
    resource_type_name="Agent",
    list_resources_func=list_agents,
    get_details_func=get_agent_details,
    render_details_func=render_agent_details_content,
    custom_obj_api=custom_obj_api,  # Pass the CustomObjectsApi
    generic_api_client=generic_api_client,  # Pass the generic ApiClient
    session_state_key_selected_resource="selected_agent_name",
)
