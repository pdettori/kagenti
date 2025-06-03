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
import asyncio
from .utils import display_tags, extract_tags, sanitize_agent_name
from .kube import load_kube_config, is_deployment_ready, get_agent_details
from .acp import run_agent_chat_stream

def display_agent_metadata(agent_details):
    """Displays the agent's description, status, creation timestamp, and tags."""
    description = agent_details.get("spec", {}).get("description", "No description available.")
    creation_timestamp = agent_details.get("metadata", {}).get("creationTimestamp", "N/A")
    status = is_deployment_ready(agent_details)
    agent_labels = agent_details.get("metadata", {}).get("labels", {})
    tags = extract_tags(agent_labels)

    st.write(f"**Description:** {description}")
    st.write(f"**Status:** {status}")
    st.write(f"**Created On:** {creation_timestamp}")
    display_tags(st, tags)
    st.markdown("---")

def initialize_session_state(sanitized_agent_name):
    """Initializes chat and log history in session state for a given agent."""
    if f"chat_history_{sanitized_agent_name}" not in st.session_state:
        st.session_state[f"chat_history_{sanitized_agent_name}"] = []
    if f"log_history_{sanitized_agent_name}" not in st.session_state:
        st.session_state[f"log_history_{sanitized_agent_name}"] = []

def display_chat_history(sanitized_agent_name):
    """Displays all messages from the current agent's chat history."""
    for message in st.session_state[f"chat_history_{sanitized_agent_name}"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_chat_interaction(agent_name: str, agent_url: str, sanitized_agent_name: str, log_display_container):
    """Manages the chat input, agent interaction, and updates chat history."""
    if prompt := st.chat_input("Say something to the agent...", key=f"chat_input_{sanitized_agent_name}"):
        st.session_state[f"chat_history_{sanitized_agent_name}"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            assistant_message_placeholder = st.empty()
            with st.spinner("Agent thinking..."):
                response = asyncio.run(
                    run_agent_chat_stream(st, sanitized_agent_name, prompt, agent_url, assistant_message_placeholder, log_display_container)
                )
        st.session_state[f"chat_history_{sanitized_agent_name}"].append({"role": "assistant", "content": response})

# --- Main Render Function ---
def render_agent_details_content(agent_name: str):
    """
    Renders the detailed view for a specific agent, including chat interface.
    """
    st.header(f"Details for Agent: {agent_name}")

    api = load_kube_config(st)
    if not api:
        return # Exit if Kubernetes API client isn't initialized

    namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
    agent_details = get_agent_details(st, api, agent_name, namespace)

    if not agent_details:
        st.warning(f"Could not load full details for agent '{agent_name}'.")
        return # Exit if agent details aren't found

    sanitized_agent_name = sanitize_agent_name(agent_name)
    agent_url = f"http://{agent_name}.localtest.me:8080"

    display_agent_metadata(agent_details)

    st.subheader("Chat with Agent")
    initialize_session_state(sanitized_agent_name)
    display_chat_history(sanitized_agent_name)

    log_display_container = st.container(border=True)
    # Display historical logs
    for log_entry in st.session_state[f"log_history_{sanitized_agent_name}"]:
        log_display_container.markdown(log_entry)

    handle_chat_interaction(agent_name, agent_url, sanitized_agent_name, log_display_container)