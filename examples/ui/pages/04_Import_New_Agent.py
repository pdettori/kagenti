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
import kubernetes.client
import os
import time  # Import time for sleep
from keycloak import KeycloakAdmin, KeycloakPostError
from lib.kube import load_kube_config


def remove_prefix(url, prefix):
    if url.startswith(prefix):
        return url[len(prefix) :]
    return url


# --- Function to Create and Monitor AgentBuild CRD ---
def create_agent_build(
    api_instance, namespace, agent_name, url, branch_or_tag, source_path, protocol_option
):
    """
    Creates an 'AgentBuild' custom resource in the specified namespace and monitors its status.
    """
    group = "beeai.beeai.dev"
    version = "v1"
    plural = "agentbuilds"
    kind = "AgentBuild"
    user = "pdettori"  # currently hardcoded

    resource_name = agent_name  # Use the extracted agent_name for the resource name

    client_secret = ""
    if os.getenv("KEYCLOAK_ENABLED"):
        external_tool_client_name = "weather-agent"
        keycloak_admin = KeycloakAdmin(
            server_url="http://keycloak.localtest.me:8080",
            username="admin",
            password="admin",
            realm_name="demo",
            user_realm_name="master",
        )
        clientID = keycloak_admin.get_client_id(external_tool_client_name)
        client_secret = keycloak_admin.get_client_secrets(clientID)["value"]

    agent_build_body = {
        "apiVersion": f"{group}/{version}",
        "kind": kind,
        "metadata": {
            "name": agent_name,
            "labels": {
                "app.kubernetes.io/created-by": "streamlit-ui",
                "app.kubernetes.io/name": "kagenti-operator",
                "kagenti.io/type": "agent",
                "kagenti.io/protocol": protocol_option,
                "kagenti.io/framework": "LangGraph",
            },
        },
        "spec": {
            "repoUrl": url,
            "sourceSubfolder": source_path,
            "repoUser": user,
            "revision": "main",
            "image": agent_name,
            "imageTag": "v0.0.1",
            "imageRegistry": "ghcr.io/" + user,
            "env": [
                {
                    "name": "SOURCE_REPO_SECRET",
                    "valueFrom": {
                        "secretKeyRef": {"name": "github-token-secret", "key": "token"}
                    },
                }
            ],
            "deployAfterBuild": True,
            "cleanupAfterBuild": True,
            "agent": {
                "name": agent_name,
                "description": f"agent_name from community",
                "env": [
                    {"name": "PORT", "value": "8000"},
                    {"name": "HOST", "value": "0.0.0.0"},
                    {
                        "name": "LLM_API_BASE",
                        "value": "http://host.docker.internal:11434/v1",
                    },
                    {"name": "LLM_API_KEY", "value": "dummy"},
                    {"name": "LLM_MODEL", "value": "llama3.2:3b-instruct-fp16"},
                    {"name": "MCP_URL", "value": "http://mcp-get-weather:8000/sse"},
                    {
                        "name": "OTEL_EXPORTER_OTLP_ENDPOINT",
                        "value": "http://otel-collector.kagenti-system.svc.cluster.local:8335",
                    },
                    {
                        "name": "KEYCLOAK_URL",
                        "value": "http://keycloak.keycloak.svc.cluster.local:8080",
                    },
                    {"name": "CLIENT_SECRET", "value": client_secret},
                    {
                        "name": "OPENAI_API_KEY",
                        "valueFrom": {
                            "secretKeyRef": {"name": "openai-secret", "key": "apikey"}
                        },
                    },
                ],
                "resources": {
                    "limits": {"cpu": "500m", "memory": "1Gi"},
                    "requests": {"cpu": "100m", "memory": "256Mi"},
                },
            },
        },
    }

    # Use a single spinner for the entire process
    with st.spinner(f"Building and deploying agent '{resource_name}'..."):
        try:
            # 1. Create the AgentBuild resource
            api_instance.create_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                body=agent_build_body,
            )
            st.success(f"AgentBuild '{resource_name}' creation request sent.")

            # 2. Set up a placeholder for status updates
            status_placeholder = st.empty()
            current_status = "Pending"

            # 3. Poll for status updates
            while current_status not in ["Completed", "Failed", "Error"]:
                try:
                    # Fetch the latest AgentBuild object
                    agent_build_obj = api_instance.get_namespaced_custom_object(
                        group=group,
                        version=version,
                        namespace=namespace,
                        plural=plural,
                        name=resource_name,
                    )
                    # Extract the buildStatus
                    current_status = agent_build_obj.get("status", {}).get(
                        "buildStatus", "Unknown"
                    )
                    status_message = agent_build_obj.get("status", {}).get(
                        "message", ""
                    )

                    # Update the status placeholder
                    status_placeholder.info(
                        f"Build Status for '{resource_name}': **{current_status}** {status_message}"
                    )

                    if current_status in ["Completed", "Failed", "Error"]:
                        break  # Exit loop if build is complete or failed

                    time.sleep(2)  # Wait for 2 seconds before polling again

                except kubernetes.client.ApiException as e:
                    if e.status == 404:
                        status_placeholder.error(
                            f"AgentBuild '{resource_name}' not found. It might have been deleted or failed to create."
                        )
                        current_status = "Error"
                    else:
                        status_placeholder.error(
                            f"Error polling AgentBuild status: {e.reason} (Status: {e.status})"
                        )
                        current_status = "Error"
                    break  # Exit loop on API error
                except Exception as e:
                    status_placeholder.error(
                        f"An unexpected error occurred during status polling: {e}"
                    )
                    current_status = "Error"
                    break  # Exit loop on unexpected error

            if current_status == "Completed":
                st.success(f"Agent '{resource_name}' built and deployed successfully!")
                return True
            else:
                st.error(
                    f"Agent build for '{resource_name}' finished with status: {current_status}. Check logs for details."
                )
                return False

        except kubernetes.client.ApiException as e:
            st.error(f"Error creating AgentBuild: {e.reason} (Status: {e.status})")
            st.code(e.body, language="json")
            if e.status == 404:
                st.warning(
                    f"Ensure the Custom Resource Definition (CRD) for '{group}/{version} {kind}' exists in your cluster."
                )
            elif e.status == 403:
                st.warning(
                    "Permission denied. Ensure your Kubernetes user/service account has 'create' permissions on 'agentbuilds.beeai.beeai.dev'."
                )
            return False
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            return False


# --- Main Page Content for Import New Agent ---
st.header("Import New Agent")
st.write(
    "This page allows you to trigger the build of a new agent by providing its source URL and path."
)
st.markdown("---")

# Input fields for URL and Source Subfolder Path
source_url = st.text_input(
    "Agent Source Repository URL",
    value="https://github.com/kagenti/agent-examples",
    key="agent_source_url",
)
branch_or_tag = st.text_input(
    "Git Branch or Tag (e.g., main, v1.0)",
    value="main",  # Default to 'main' for convenience
    key="agent_branch_or_tag",
)
protocol_option = st.selectbox(
        "Select protocol:",
        options = [
            "acp",
            "a2a",
        ],
        key="selected_protocol_option",
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
        "a2a/a2a_contact_extractor",
        "a2a/a2a_currency_converter",
    ]

    selected_subfolder_option = st.selectbox(
        "Select an example subfolder:",
        options=example_subfolders,
        key="selected_subfolder_option",
    )

    if selected_subfolder_option != "Select from examples or type manually":
        selected_subfolder = selected_subfolder_option

    manual_subfolder_input = st.text_input(
        "Or manually enter Source Subfolder Path (relative to repository root)",
        value=(
            selected_subfolder if selected_subfolder else ""
        ),  # Pre-fill if an example was selected
        placeholder="e.g., agents/my-new-agent",
        key="manual_agent_source_subfolder_path",
    )

# Determine the final source_subfolder_path to use
final_source_subfolder_path = (
    manual_subfolder_input if manual_subfolder_input else selected_subfolder
)


# Submit button
if st.button("Build New Agent", key="build_new_agent_btn"):
    if source_url and branch_or_tag and final_source_subfolder_path:
        # Extract agent_name from the last part of the final_source_subfolder_path
        source_url = remove_prefix(source_url, "https://")
        agent_name = os.path.basename(final_source_subfolder_path.strip("/\\")).replace(
            "_", "-"
        )

        if not agent_name:
            st.warning(
                "Could not extract a valid agent name from the Source Subfolder Path. Please ensure it's not empty or just slashes."
            )
        else:
            api = load_kube_config(st)
            if api:
                namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
                st.info(
                    f"Attempting to build agent '{agent_name}' from URL: `{source_url}`, branch/tag: `{branch_or_tag}`, and path: `{final_source_subfolder_path}` in namespace: `{namespace}`."
                )
                # Call the modified function to create and monitor the build
                create_agent_build(
                    api,
                    namespace,
                    agent_name,
                    source_url,
                    branch_or_tag,
                    final_source_subfolder_path,
                    protocol_option
                )
            else:
                st.error(
                    "Kubernetes API client not initialized. Cannot create AgentBuild."
                )
    else:
        st.warning(
            "Please provide the Source Repository URL, Git Branch/Tag, and Source Subfolder Path."
        )

st.markdown("---")
