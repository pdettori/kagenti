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
import os
from lib.kube import is_deployment_ready, load_kube_config

# TODO - this page is based on the old abstraction of agent - will move to the new operator/CRD model for tools

# --- Function to List Tools ---
def list_tools(api_instance, namespace="default"):
    """
    Lists custom resources of kind 'Agent' from the specified namespace.
    Filters for tools with the label 'kagenti.io/type=tool'.
    """
    group = "beeai.beeai.dev"
    version = "v1"
    plural = "agents" # Plural form of your custom resource 'Agent'

    try:
        # List namespaced custom objects
        # Note: Kubernetes API client's list_namespaced_custom_object does not directly support
        # label selectors as a parameter for all versions/CRDs.
        # We will fetch all and filter in Python for simplicity and broader compatibility.
        api_response = api_instance.list_namespaced_custom_object(group, version, namespace, plural)
        
        # Filter tools by the required label 'kagenti.io/type=tool'
        filtered_tools = []
        for tool in api_response["items"]:
            labels = tool.get("metadata", {}).get("labels", {})
            if labels.get("kagenti.io/type") == "tool":
                filtered_tools.append(tool)
        return filtered_tools
    except kubernetes.client.ApiException as e:
        st.error(f"Error fetching tools from Kubernetes: {e}")
        if e.status == 404:
            st.warning(f"Ensure the Custom Resource Definition (CRD) for '{group}/{version} Agents' exists in your cluster.")
        elif e.status == 403:
            st.warning("Permission denied. Ensure your Kubernetes user/service account has 'get' and 'list' permissions on 'tools.beeai.beeai.dev'.")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return []

# --- Main Page Content ---
st.header("Tool Catalog")
st.write("Welcome to the Tool Catalog page. Here you can view and manage your tools.")
st.markdown("---")

# show the list of available tools
st.subheader("Available Tools")

# Load Kubernetes config and get API instance
api = load_kube_config(st)

if api:
    namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
    st.info(f"Attempting to list Tools in namespace: `{namespace}` (filtered by label `kagenti.io/type=tool`)")

    tools = list_tools(api, namespace)

    if tools:
        for tool in tools:
            tool_name = tool.get("metadata", {}).get("name", "N/A")
            tool_description = tool.get("spec", {}).get("description", "No description provided.")
            tool_labels = tool.get("metadata", {}).get("labels", {})

            protocol_tag = tool_labels.get("kagenti.io/protocol", "N/A")
            framework_tag = tool_labels.get("kagenti.io/framework", "N/A")
            status = is_deployment_ready(tool)

            # Display each tool in a clickable container (box)
            with st.container(border=True):
                col_name, col_button = st.columns([4, 1])
                with col_name:
                    st.markdown(f"### {tool_name}")
                    st.write(f"**Description:** {tool_description}")
                    st.write(f"**Status:** {status}")
                    st.markdown(f"**Tags:** <span style='background-color:#e0f7fa; padding: 4px 8px; border-radius: 5px; margin-right: 5px; font-size: 0.8em;'>Protocol: {protocol_tag}</span> <span style='background-color:#e0f7fa; padding: 4px 8px; border-radius: 5px; font-size: 0.8em;'>Framework: {framework_tag}</span>", unsafe_allow_html=True)
                with col_button:
                    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                    # When "View Details" is clicked, set the session state
                    if st.button("View Details", key=f"view_details_{tool_name}"):
                        st.session_state.selected_tool_name = tool_name
                        st.rerun() # Rerun the app to show details
    else:
        st.info(f"No 'Agent' custom resources with label `kagenti.io/type=tool` found in the '{namespace}' namespace.")
else:
    st.warning("Kubernetes API client not initialized. Cannot fetch tool list.")


