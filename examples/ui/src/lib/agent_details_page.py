# ui/lib/agent_details_page.py

import streamlit as st
import asyncio
import logging
from .utils import (
    sanitize_for_session_state_key,
    initialize_chat_session_state,
    display_chat_history,
    append_to_chat_history,
    display_log_history
)
from .kube import get_custom_objects_api, get_agent_details, get_kubernetes_namespace, is_running_in_cluster # Changed get_kube_api_client to get_custom_objects_api
from .acp_utils import run_agent_chat_stream_acp, display_acp_agent_metadata
from .a2a_utils import run_agent_chat_stream_a2a, render_a2a_agent_card
from .common_ui import display_resource_metadata
from . import constants # Import constants

logger = logging.getLogger(__name__)

def _handle_chat_interaction(
    st_object,
    agent_k8s_name: str, # Kubernetes resource name
    agent_chat_name: str, # Name used for chat with ACP/A2A (might be same or different)
    agent_url: str,
    session_key_prefix: str,
    log_display_container,
    protocol: str
):
    """Manages the chat input, agent interaction, and updates chat history."""
    prompt_key = f"chat_input_{session_key_prefix}"
    if prompt := st_object.chat_input("Say something to the agent...", key=prompt_key):
        append_to_chat_history(session_key_prefix, "user", prompt)
        with st_object.chat_message("user"):
            st_object.markdown(prompt)

        with st_object.chat_message("assistant"):
            assistant_message_placeholder = st_object.empty()
            response = "" # Initialize response
            with st.spinner("Agent thinking..."):
                try:
                    if not agent_url:
                        response = "Agent URL is not configured. Cannot initiate chat."
                        assistant_message_placeholder.error(response)
                        logger.error(f"Agent URL not available for agent {agent_k8s_name}")
                    elif protocol == "acp":
                        response = asyncio.run(
                            run_agent_chat_stream_acp(
                                st, session_key_prefix, prompt, agent_chat_name, agent_url,
                                assistant_message_placeholder, log_display_container
                            )
                        )
                    elif protocol == "a2a":
                        response = asyncio.run(
                            run_agent_chat_stream_a2a(
                                st, session_key_prefix, prompt, agent_url,
                                assistant_message_placeholder, log_display_container
                            )
                        )
                    else:
                        response = "Unknown agent protocol for chat."
                        assistant_message_placeholder.error(response)
                        logger.error(f"Unknown protocol '{protocol}' for agent {agent_k8s_name}")

                except Exception as e:
                    response = f"Error during chat interaction: {e}"
                    logger.error(f"Chat interaction error for agent {agent_k8s_name}: {e}", exc_info=True)
                    assistant_message_placeholder.error(response)

        if response:
            append_to_chat_history(session_key_prefix, "assistant", response)
        else:
            fallback_response = "No response received from agent, or URL was missing."
            assistant_message_placeholder.markdown(fallback_response)
            append_to_chat_history(session_key_prefix, "assistant", fallback_response)


# --- Main Render Function for Agent Details ---
def render_agent_details_content(agent_k8s_name: str):
    """
    Renders the detailed view for a specific agent, including chat interface.
    Args:
        agent_k8s_name: The Kubernetes name of the agent.
    """
    st.header(f"Agent: {agent_k8s_name}")

    # Use the correct function to get the CustomObjectsApi client
    custom_obj_api = get_custom_objects_api() 
    if not custom_obj_api:
        st.error("Kubernetes API client (CustomObjectsApi) not available. Cannot load agent details.")
        return

    namespace = get_kubernetes_namespace()
    # Pass the CustomObjectsApi client to get_agent_details
    agent_details_data = get_agent_details(st, custom_obj_api, agent_k8s_name, namespace) 

    if not agent_details_data:
        st.warning(f"Could not load full details for agent '{agent_k8s_name}'. It might have been deleted or is not accessible.")
        return

    session_key_prefix = sanitize_for_session_state_key(agent_k8s_name)
    tags = display_resource_metadata(st, agent_details_data)
    protocol = tags.get("protocol", "").lower()

    # Determine agent URL based on environment
    spec = agent_details_data.get("spec", {})
    agent_service_name_from_spec = spec.get("serviceName")
    agent_service_host_name = agent_service_name_from_spec or agent_k8s_name
    
    # Determine port based on environment, allowing override from spec.servicePort
    running_in_cluster = is_running_in_cluster()
    default_port = constants.DEFAULT_IN_CLUSTER_PORT if running_in_cluster else constants.DEFAULT_OFF_CLUSTER_PORT
    agent_port = spec.get("servicePort", default_port) 
    
    agent_url = None 
    if agent_service_host_name:
        scheme = "http://" # Assuming http for now
        if running_in_cluster:
            agent_url = f"{scheme}{agent_service_host_name}.{namespace}.svc.cluster.local:{agent_port}"
        else:
            # For local/off-cluster, localtest.me typically resolves to localhost.
            # The port here is the one you'd use for port-forwarding or local exposure.
            agent_url = f"{scheme}{agent_service_host_name}.localtest.me:{agent_port}"
        
        logger.info(f"Agent URL for '{agent_k8s_name}': {agent_url} (in-cluster: {running_in_cluster}, port: {agent_port})")
        if not running_in_cluster:
             st.caption(f"Attempting to connect via local URL: `{agent_url}`. Ensure port-forwarding or Ingress to this port is active if the agent runs in-cluster.")

    else:
        st.error(f"Could not determine service name for agent '{agent_k8s_name}'. Cannot construct agent URL.")
        logger.error(f"Service name for agent '{agent_k8s_name}' is missing in CRD spec and as resource name.")


    # Display protocol-specific card/metadata
    if agent_url: 
        if protocol == "acp":
            acp_logical_name = spec.get("acpAgentName", agent_k8s_name) # Use spec field or k8s name for ACP
            asyncio.run(display_acp_agent_metadata(st, acp_logical_name, agent_url))
        elif protocol == "a2a":
            asyncio.run(render_a2a_agent_card(st, agent_url))
        elif not protocol:
            st.warning("Agent protocol not specified in tags. Chat functionality may be limited.")
        else:
            st.markdown(f"**Protocol:** {protocol.upper()} (Details UI not implemented for this protocol)")
    else:
        st.error("Agent URL could not be determined. Cannot display protocol-specific details or enable chat.")


    st.markdown("---")
    st.subheader("Chat with Agent")

    initialize_chat_session_state(session_key_prefix)
    display_chat_history(session_key_prefix)

    log_display_container = st.container(border=True) 
    with log_display_container:
        st.caption("Interaction Logs:")
        display_log_history(st, session_key_prefix)

    agent_chat_name_for_sdk = spec.get("acpAgentName", agent_k8s_name) if protocol == "acp" else agent_k8s_name

    if agent_url and protocol in ["acp", "a2a"]:
        _handle_chat_interaction(
            st, agent_k8s_name, agent_chat_name_for_sdk, agent_url,
            session_key_prefix, log_display_container, protocol
        )
    elif not agent_url:
        st.info("Chat not enabled: Agent URL could not be determined.")
    else: 
        st.info(f"Chat not enabled for agents with protocol '{protocol or 'unknown'}'.")

