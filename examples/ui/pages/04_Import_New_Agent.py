import streamlit as st
import kubernetes.client
import kubernetes.config
import os


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

def remove_prefix(url, prefix):
    if url.startswith(prefix):
        return url[len(prefix):]
    return url

# --- Function to Create AgentBuild CRD ---
def create_agent_build(api_instance, namespace, agent_name, url, branch_or_tag, source_path):
    """
    Creates an 'AgentBuild' custom resource in the specified namespace.
    """
    group = "beeai.beeai.dev"
    version = "v1"
    plural = "agentbuilds" 
    kind = "AgentBuild"
    user = "pdettori" # currently hardcoded

    # Use the extracted agent_name for the resource name
    resource_name = agent_name

    agent_build_body = {
        "apiVersion": f"{group}/{version}",
        "kind": kind,
        "metadata": {
            "name": agent_name,
            "labels": {
                "app.kubernetes.io/created-by": "streamlit-ui",
                "app.kubernetes.io/name": "kagenti-operator",
                "kagenti.io/type": "agent",
                "kagenti.io/protocol": "acp",
                "kagenti.io/framework": "LangGraph",
            }
        },
        "spec": {
            "repoUrl": url,
            "sourceSubfolder": source_path,
            "repoUser": user,
            "revision": "main",
            "image": "acp-ollama-weather-service",
            "imageTag": "v0.0.1",
            "imageRegistry": "ghcr.io/"+user,
            "env": [
            {
                "name": "SOURCE_REPO_SECRET",
                "valueFrom": {
                "secretKeyRef": {
                    "name": "github-token-secret",
                    "key": "token"
                }
                }
            }
            ],
            "deployAfterBuild": True,
            "cleanupAfterBuild": True,
            "agent": {
            "name": "acp-weather-service",
            "description": "acp-weather-service from ACP community",
            "env": [
                {
                "name": "PORT",
                "value": "8000"
                },
                {
                "name": "HOST",
                "value": "0.0.0.0"
                },
                {
                "name": "LLM_API_BASE",
                "value": "http://host.docker.internal:11434/v1"
                },
                {
                "name": "LLM_API_KEY",
                "value": "dummy"
                },
                {
                "name": "LLM_MODEL",
                "value": "llama3.2:3b-instruct-fp16"
                },
                {
                "name": "MCP_URL",
                "value": "http://mcp-get-weather:8000/sse"
                },
                {
                "name": "OTEL_EXPORTER_OTLP_ENDPOINT",
                "value": "http://otel-collector.kagenti-system.svc.cluster.local:8335"
                }
            ],
            "resources": {
                "limits": {
                "cpu": "500m",
                "memory": "1Gi"
                },
                "requests": {
                "cpu": "100m",
                "memory": "256Mi"
                }
            }
            }
        }
    }

    try:
        with st.spinner(f"Creating AgentBuild '{resource_name}' in namespace '{namespace}'..."):
            api_response = api_instance.create_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                body=agent_build_body
            )
            st.success(f"AgentBuild '{resource_name}' created successfully!")
            st.json(api_response) # Display the created object for verification
            return True
    except kubernetes.client.ApiException as e:
        st.error(f"Error creating AgentBuild: {e.reason} (Status: {e.status})")
        st.code(e.body, language="json")
        if e.status == 404:
            st.warning(f"Ensure the Custom Resource Definition (CRD) for '{group}/{version} {kind}' exists in your cluster.")
        elif e.status == 403:
            st.warning("Permission denied. Ensure your Kubernetes user/service account has 'create' permissions on 'agentbuilds.beeai.beeai.dev'.")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return False

# --- Main Page Content for Import New Agent ---
st.header("Import New Agent")
st.write("This page allows you to trigger the build of a new agent by providing its source URL and path.")
st.markdown("---")

# Input fields for URL and Source Subfolder Path
source_url = st.text_input(
    "Agent Source Repository URL",
    value="https://github.com/kagenti/agent-examples",
    key="agent_source_url"
)
branch_or_tag = st.text_input(
    "Git Branch or Tag (e.g., main, v1.0)",
    value="main", # Default to 'main' for convenience
    key="agent_branch_or_tag"
)

# Simulated subfolder browsing
selected_subfolder = None
manual_subfolder_input = ""

if source_url and branch_or_tag:
    st.markdown("---")
    st.subheader("Browse Subfolders")
    # st.info("Live Git repository browsing from Streamlit's frontend is complex due to security and API limitations. "
    #         "Below is a simulated selection or you can manually enter the path.")

    # Example subfolders (replace with actual logic if you have a backend)
    example_subfolders = [
        "acp/acp_ollama_researcher",
        "acp/acp_weather_service",
        "a2a/langgraph",
        "a2a/marvin"
    ]

    selected_subfolder_option = st.selectbox(
        "Select an example subfolder:",
        options=example_subfolders,
        key="selected_subfolder_option"
    )

    if selected_subfolder_option != "Select from examples or type manually":
        selected_subfolder = selected_subfolder_option

    manual_subfolder_input = st.text_input(
        "Or manually enter Source Subfolder Path (relative to repository root)",
        value=selected_subfolder if selected_subfolder else "", # Pre-fill if an example was selected
        placeholder="e.g., agents/my-new-agent",
        key="manual_agent_source_subfolder_path"
    )

# Determine the final source_subfolder_path to use
final_source_subfolder_path = manual_subfolder_input if manual_subfolder_input else selected_subfolder


# Submit button
if st.button("Build New Agent", key="build_new_agent_btn"):
    if source_url and branch_or_tag and final_source_subfolder_path:
        # Extract agent_name from the last part of the final_source_subfolder_path
        source_url = remove_prefix(source_url,'https://')
        agent_name = os.path.basename(final_source_subfolder_path.strip('/\\')).replace('_','-')

        if not agent_name:
            st.warning("Could not extract a valid agent name from the Source Subfolder Path. Please ensure it's not empty or just slashes.")
        else:
            api = load_kube_config()
            if api:
                namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
                st.info(f"Attempting to build agent '{agent_name}' from URL: `{source_url}`, branch/tag: `{branch_or_tag}`, and path: `{final_source_subfolder_path}` in namespace: `{namespace}`.")
                create_agent_build(api, namespace, agent_name, source_url, branch_or_tag, final_source_subfolder_path)
            else:
                st.error("Kubernetes API client not initialized. Cannot create AgentBuild.")
    else:
        st.warning("Please provide the Source Repository URL, Git Branch/Tag, and Source Subfolder Path.")

st.markdown("---")

