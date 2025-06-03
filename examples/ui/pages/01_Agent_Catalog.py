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
from lib.agent_details_page import render_agent_details_content
from lib.utils import display_tags, extract_tags
from lib.kube import is_deployment_ready, load_kube_config, list_agents


st.header("Agent Catalog")
st.write("Welcome to the Agent Catalog page. Here you can view and manage your agents.")
st.markdown("---")

# Initialize session state for selected agent
if 'selected_agent_name' not in st.session_state:
    st.session_state.selected_agent_name = None

# Check if an agent is selected for details view
if st.session_state.selected_agent_name:
    # If an agent is selected, render its details
    render_agent_details_content(st.session_state.selected_agent_name)
    st.markdown("---")
    # Button to go back to the list of agents
    if st.button("Back to Agent List", key="back_to_agent_list_btn"):
        st.session_state.selected_agent_name = None # Clear selected agent
        st.rerun() # Rerun the app to show the list

else:
    # If no agent is selected, show the list of available agents
    st.subheader("Available Agents")

    # Load Kubernetes config and get API instance
    api = load_kube_config(st)

    if api:
        namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
        st.info(f"Attempting to list Agents in namespace: `{namespace}` (filtered by label `kagenti.io/type=agent`)")

        agents = list_agents(st, api, namespace)

        if agents:
            for agent in agents:
                agent_name = agent.get("metadata", {}).get("name", "N/A")
                agent_description = agent.get("spec", {}).get("description", "No description provided.")
                agent_labels = agent.get("metadata", {}).get("labels", {})
                tags = extract_tags(agent_labels)
                status = is_deployment_ready(agent)

                # Display each agent in a clickable container (box)
                with st.container(border=True):
                    col_name, col_button = st.columns([4, 1])
                    with col_name:
                        st.markdown(f"### {agent_name}")
                        st.write(f"**Description:** {agent_description}")
                        st.write(f"**Status:** {status}")
                        display_tags(st, tags)
                    with col_button:
                        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                        # When "View Details" is clicked, set the session state
                        if st.button("View Details", key=f"view_details_{agent_name}"):
                            st.session_state.selected_agent_name = agent_name
                            st.rerun() # Rerun the app to show details
        else:
            st.info(f"No 'Agent' custom resources with label `kagenti.io/type=agent` found in the '{namespace}' namespace.")
    else:
        st.warning("Kubernetes API client not initialized. Cannot fetch agent list.")


