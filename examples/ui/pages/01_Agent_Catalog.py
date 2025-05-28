import streamlit as st
import kubernetes.client
import kubernetes.config
import os
# Import the function from the 'lib' directory
from lib._agent_details_page import render_agent_details_content

# --- Kubernetes Configuration ---
def load_kube_config():
    """
    Loads Kubernetes configuration.
    It tries in-cluster config first, then kubeconfig file.
    """
    try:
        kubernetes.config.load_incluster_config()
        st.success("Loaded in-cluster Kubernetes config.")
    except kubernetes.config.ConfigException:
        try:
            kubernetes.config.load_kube_config()
            st.success("Loaded kubeconfig from default path.")
        except kubernetes.config.ConfigException:
            st.error("Could not load Kubernetes configuration. "
                     "Ensure you are running inside a cluster or have a valid kubeconfig file.")
            return None
    return kubernetes.client.CustomObjectsApi()

# --- Function to List Agents ---
def list_agents(api_instance, namespace="default"):
    """
    Lists custom resources of kind 'Agent' from the specified namespace.
    Filters for agents with the label 'kagenti.io/type=agent'.
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
        
        # Filter agents by the required label 'kagenti.io/type=agent'
        filtered_agents = []
        for agent in api_response["items"]:
            labels = agent.get("metadata", {}).get("labels", {})
            if labels.get("kagenti.io/type") == "agent":
                filtered_agents.append(agent)
        return filtered_agents
    except kubernetes.client.ApiException as e:
        st.error(f"Error fetching agents from Kubernetes: {e}")
        if e.status == 404:
            st.warning(f"Ensure the Custom Resource Definition (CRD) for '{group}/{version} Agents' exists in your cluster.")
        elif e.status == 403:
            st.warning("Permission denied. Ensure your Kubernetes user/service account has 'get' and 'list' permissions on 'agents.beeai.beeai.dev'.")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return []

# --- Main Page Content ---
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
    api = load_kube_config()

    if api:
        namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
        st.info(f"Attempting to list Agents in namespace: `{namespace}` (filtered by label `kagenti.io/type=agent`)")

        agents = list_agents(api, namespace)

        if agents:
            for agent in agents:
                agent_name = agent.get("metadata", {}).get("name", "N/A")
                agent_description = agent.get("spec", {}).get("description", "No description provided.")
                agent_labels = agent.get("metadata", {}).get("labels", {})

                protocol_tag = agent_labels.get("kagenti.io/protocol", "N/A")
                framework_tag = agent_labels.get("kagenti.io/framework", "N/A")

                # Display each agent in a clickable container (box)
                with st.container(border=True):
                    col_name, col_button = st.columns([4, 1])
                    with col_name:
                        st.markdown(f"### {agent_name}")
                        st.write(f"**Description:** {agent_description}")
                        st.markdown(f"**Tags:** <span style='background-color:#e0f7fa; padding: 4px 8px; border-radius: 5px; margin-right: 5px; font-size: 0.8em;'>Protocol: {protocol_tag}</span> <span style='background-color:#e0f7fa; padding: 4px 8px; border-radius: 5px; font-size: 0.8em;'>Framework: {framework_tag}</span>", unsafe_allow_html=True)
                    with col_button:
                        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                        # When "View Details" is clicked, set the session state
                        if st.button("View Details", key=f"view_details_{agent_name}"):
                            st.session_state.selected_agent_name = agent_name
                            st.rerun() # Rerun the app to show details
        else:
            st.info(f"No 'Agent' custom resources with label `kagenti.io/type=agent` found in the '{namespace}' namespace.")
            st.markdown(
                """
                To create a sample Agent custom resource, you can use `kubectl apply -f` and ensure it has the required labels:
                ```yaml
                apiVersion: beeai.beeai.dev/v1
                kind: Agent
                metadata:
                  name: my-first-agent
                  labels:
                    kagenti.io/type: agent
                    kagenti.io/protocol: http
                    kagenti.io/framework: langchain
                spec:
                  description: "This is a sample agent for demonstration purposes."
                  # Add other spec fields as per your CRD
                ---
                apiVersion: beeai.beeai.dev/v1
                kind: Agent
                metadata:
                  name: another-agent
                  labels:
                    kagenti.io/type: agent
                    kagenti.io/protocol: grpc
                    kagenti.io/framework: autogen
                spec:
                  description: "A second example agent with a different purpose."
                ```
                """
            )
    else:
        st.warning("Kubernetes API client not initialized. Cannot fetch agent list.")

st.markdown("---")
st.info("You can import new agents via the 'Import New Agent' option")
