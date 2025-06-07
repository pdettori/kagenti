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
import time
from typing import Optional, List, Dict, Any, Callable
from keycloak import KeycloakAdmin
from . import constants
from .kube import (
    get_custom_objects_api,
    get_core_v1_api,
    get_all_namespaces,
    get_secret_data,
    _handle_kube_api_exception,
    _display_kube_config_status_once,
)
from .utils import sanitize_for_k8s_name, remove_url_prefix, get_resource_name_from_path
import logging

logger = logging.getLogger(__name__)


def _get_keycloak_client_secret(st_object, client_name: str) -> str:
    if not os.getenv("KEYCLOAK_ENABLED", "false").lower() == "true":
        return ""
    try:
        keycloak_admin = KeycloakAdmin(
            server_url=os.getenv(
                "KEYCLOAK_SERVER_URL", "http://keycloak.localtest.me:8080"
            ),
            username=os.getenv("KEYCLOAK_ADMIN_USER", "admin"),
            password=os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin"),
            realm_name=os.getenv("KEYCLOAK_REALM_NAME", "demo"),
            user_realm_name="master",
            verify=True,
        )
        client_id_in_realm = keycloak_admin.get_client_id(client_name)
        if not client_id_in_realm:
            st_object.warning(
                f"Keycloak client '{client_name}' not found for agent runtime secret."
            )
            return ""
        secrets = keycloak_admin.get_client_secrets(client_id_in_realm)
        return secrets.get("value", "") if secrets else ""
    except Exception as e:
        st_object.error(
            f"Failed to get Keycloak client secret for '{client_name}' (agent runtime): {e}"
        )
        return ""


def _construct_build_resource_body(
    st_object,
    core_v1_api: Optional[kubernetes.client.CoreV1Api],
    build_namespace: str,
    resource_name: str,
    resource_type: str,
    repo_url: str,
    repo_branch: str,
    source_subfolder: str,
    protocol: str,
    framework: str,
    description: str,
    additional_env_vars: Optional[list] = None,
    image_tag: str = constants.DEFAULT_IMAGE_TAG,
) -> Optional[dict]:
    k8s_resource_name = sanitize_for_k8s_name(resource_name)
    image_name = k8s_resource_name
    repo_user = get_secret_data(
        core_v1_api,
        build_namespace,
        constants.GIT_USER_SECRET_NAME,
        constants.GIT_USER_SECRET_KEY,
    )
    if not repo_user:
        st_object.error(
            f"Failed to fetch GitHub username from secret '{constants.GIT_USER_SECRET_NAME}' (key: '{constants.GIT_USER_SECRET_KEY}') in namespace '{build_namespace}'. Ensure secret exists and K8s client is functional."
        )
        return None
    st_object.info(f"Using GitHub username '{repo_user}' from secret for build.")
    image_registry_prefix = f"ghcr.io/{repo_user}"
    client_secret_for_env = _get_keycloak_client_secret(
        st_object, f"{k8s_resource_name}-client"
    )
    final_env_vars = list(constants.DEFAULT_ENV_VARS)
    if resource_type == constants.RESOURCE_TYPE_AGENT:
        final_env_vars.extend(constants.DEFAULT_AGENT_ENV_VARS_EXT)
    elif resource_type == constants.RESOURCE_TYPE_TOOL:
        final_env_vars.extend(constants.DEFAULT_TOOL_ENV_VARS_EXT)
    if additional_env_vars:
        final_env_vars.extend(additional_env_vars)
    if client_secret_for_env:
        final_env_vars.append({"name": "CLIENT_SECRET", "value": client_secret_for_env})
    body = {
        "apiVersion": f"{constants.CRD_GROUP}/{constants.CRD_VERSION}",
        "kind": "AgentBuild",
        "metadata": {
            "name": k8s_resource_name,
            "namespace": build_namespace,
            "labels": {
                constants.APP_KUBERNETES_IO_CREATED_BY: constants.STREAMLIT_UI_CREATOR_LABEL,
                constants.APP_KUBERNETES_IO_NAME: constants.KAGENTI_OPERATOR_LABEL_NAME,
                constants.KAGENTI_TYPE_LABEL: resource_type,
                constants.KAGENTI_PROTOCOL_LABEL: protocol,
                constants.KAGENTI_FRAMEWORK_LABEL: framework,
            },
        },
        "spec": {
            "repoUrl": remove_url_prefix(repo_url),
            "sourceSubfolder": source_subfolder,
            "repoUser": repo_user,
            "revision": repo_branch,
            "image": image_name,
            "imageTag": image_tag,
            "imageRegistry": image_registry_prefix,
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
                "name": k8s_resource_name,
                "description": description
                or f"{resource_type.capitalize()} '{resource_name}' from community source",
                "env": final_env_vars,
                "resources": {
                    "limits": constants.DEFAULT_RESOURCE_LIMITS,
                    "requests": constants.DEFAULT_RESOURCE_REQUESTS,
                },
            },
        },
    }
    return body


def trigger_and_monitor_build(
    st_object,
    custom_obj_api: Optional[kubernetes.client.CustomObjectsApi],
    core_v1_api: Optional[kubernetes.client.CoreV1Api],
    build_namespace: str,
    resource_name_suggestion: str,
    resource_type: str,
    repo_url: str,
    repo_branch: str,
    source_subfolder: str,
    protocol: str,
    framework: str,
    description: str = "",
):
    if not custom_obj_api:
        st_object.error(
            "Kubernetes CustomObjectsApi client not initialized. Cannot trigger build."
        )
        return False
    if not core_v1_api:
        st_object.error(
            "Kubernetes CoreV1Api client not initialized. Cannot fetch secrets for build."
        )
        return False
    k8s_resource_name = sanitize_for_k8s_name(resource_name_suggestion)
    if not k8s_resource_name:
        st_object.error("Invalid resource name after sanitization. Cannot proceed.")
        return False
    build_cr_body = _construct_build_resource_body(
        st_object=st_object,
        core_v1_api=core_v1_api,
        build_namespace=build_namespace,
        resource_name=k8s_resource_name,
        resource_type=resource_type,
        repo_url=repo_url,
        repo_branch=repo_branch,
        source_subfolder=source_subfolder,
        protocol=protocol,
        framework=framework,
        description=description,
    )
    if not build_cr_body:
        st_object.error(
            f"Failed to construct build resource body for '{k8s_resource_name}'. Check previous errors."
        )
        return False
    with st_object.spinner(
        f"Submitting build for {resource_type} '{k8s_resource_name}' in namespace '{build_namespace}'..."
    ):
        try:
            custom_obj_api.create_namespaced_custom_object(
                group=constants.CRD_GROUP,
                version=constants.CRD_VERSION,
                namespace=build_namespace,
                plural=constants.AGENTBUILDS_PLURAL,
                body=build_cr_body,
            )
            st_object.success(
                f"{resource_type.capitalize()}Build '{k8s_resource_name}' creation request sent to namespace '{build_namespace}'."
            )
        except kubernetes.client.ApiException as e:
            _handle_kube_api_exception(
                st_object,
                e,
                f"{resource_type.capitalize()}Build '{k8s_resource_name}'",
                action="creating",
            )
            return False
        except Exception as e:
            st_object.error(
                f"An unexpected error occurred creating build for '{k8s_resource_name}': {e}"
            )
            return False
    status_placeholder = st_object.empty()
    current_build_status = "Pending"
    max_retries = 120
    retries = 0
    with st_object.spinner(
        f"Waiting for {resource_type} '{k8s_resource_name}' in '{build_namespace}' to build and deploy..."
    ):
        while (
            current_build_status not in ["Completed", "Failed", "Error"]
            and retries < max_retries
        ):
            retries += 1
            try:
                build_obj = custom_obj_api.get_namespaced_custom_object(
                    group=constants.CRD_GROUP,
                    version=constants.CRD_VERSION,
                    namespace=build_namespace,
                    plural=constants.AGENTBUILDS_PLURAL,
                    name=k8s_resource_name,
                )
                status_data = build_obj.get("status", {})
                current_build_status = status_data.get("buildStatus", "Unknown")
                status_message = status_data.get("message", "")
                deployment_status = status_data.get("deploymentStatus", "")
                status_placeholder.info(
                    f"Build Status for '{k8s_resource_name}': **{current_build_status}**\nMessage: {status_message}\nDeployment Status: **{deployment_status}**"
                )
                if current_build_status in ["Completed", "Failed", "Error"]:
                    break
                time.sleep(constants.POLL_INTERVAL_SECONDS)
            except kubernetes.client.ApiException as e:
                if e.status == 404:
                    status_placeholder.error(
                        f"{resource_type.capitalize()}Build '{k8s_resource_name}' not found during polling."
                    )
                else:
                    status_placeholder.error(
                        f"API error polling build status for '{k8s_resource_name}': {e.reason}"
                    )
                current_build_status = "Error"
                break
            except Exception as e:
                status_placeholder.error(
                    f"Unexpected error polling build status for '{k8s_resource_name}': {e}"
                )
                current_build_status = "Error"
                break
        if retries >= max_retries and current_build_status not in [
            "Completed",
            "Failed",
            "Error",
        ]:
            status_placeholder.error(
                f"Timeout waiting for build of '{k8s_resource_name}' to complete."
            )
            return False
    if current_build_status == "Completed":
        final_deployment_status = build_obj.get("status", {}).get(
            "deploymentStatus", ""
        )
        if "Ready" in final_deployment_status or not final_deployment_status:
            st_object.success(
                f"{resource_type.capitalize()} '{k8s_resource_name}' built and deployed successfully in namespace '{build_namespace}'!"
            )
            return True
        else:
            st_object.warning(
                f"{resource_type.capitalize()} '{k8s_resource_name}' built in '{build_namespace}', but deployment status is '{final_deployment_status}'. Manual check might be needed."
            )
            return True
    else:
        st_object.error(
            f"{resource_type.capitalize()} build for '{k8s_resource_name}' in '{build_namespace}' finished with status: {current_build_status}. Check operator logs."
        )
        return False


def render_import_form(
    st_object,
    resource_type: str,
    default_protocol: str,
    default_framework: str,
    k8s_api_client: Optional[kubernetes.client.ApiClient],
    k8s_client_status_msg: Optional[str],
    k8s_client_status_icon: Optional[str],
    example_subfolders: List[str] = [],
    protocol_options: Optional[List[str]] = None,
):
    """Renders the common UI form for importing a new Agent or Tool."""
    st_object.header(f"Import New {resource_type}")

    # Display K8s client connection status
    _display_kube_config_status_once(
        k8s_client_status_msg, k8s_client_status_icon, bool(k8s_api_client)
    )

    # --- Namespace Selector for Build/Deployment ---
    available_build_namespaces = ["default"]  # Fallback
    if k8s_api_client:
        available_build_namespaces = get_all_namespaces(k8s_api_client)
        if (
            not available_build_namespaces
        ):  # If get_all_namespaces returned empty (e.g. due to permissions)
            available_build_namespaces = ["default"]
            st_object.caption(
                "Could not list all namespaces, defaulting to 'default'. Check K8s permissions if other namespaces are expected."
            )
    else:
        st_object.caption(
            "Kubernetes client not available. Build will target 'default' namespace. Please check K8s connection."
        )

    default_build_ns = "default"
    initial_selected_build_ns = st.session_state.get(
        "selected_build_k8s_namespace", default_build_ns
    )

    # Ensure initial_selected_build_ns is valid within the available options
    if initial_selected_build_ns not in available_build_namespaces:
        if default_build_ns in available_build_namespaces:
            initial_selected_build_ns = default_build_ns
        elif (
            available_build_namespaces
        ):  # if list is not empty but doesn't contain current or default
            initial_selected_build_ns = available_build_namespaces[0]

    build_ns_index = 0
    if available_build_namespaces:  # Should always have at least "default"
        try:
            build_ns_index = available_build_namespaces.index(initial_selected_build_ns)
        except ValueError:
            build_ns_index = 0

    newly_selected_build_namespace = st_object.selectbox(
        f"Select Namespace to Deploy {resource_type}:",
        options=available_build_namespaces,
        index=build_ns_index,
        key=f"{resource_type.lower()}_build_namespace_selector",
        help=f"The AgentBuild resource and the resulting {resource_type} will be created in this namespace. The '{constants.GIT_USER_SECRET_NAME}' must also exist here.",
    )

    if (
        newly_selected_build_namespace
        and newly_selected_build_namespace
        != st.session_state.get("selected_build_k8s_namespace")
    ):
        st.session_state.selected_build_k8s_namespace = newly_selected_build_namespace
        st.toast(f"Build namespace set to: {newly_selected_build_namespace}")

    build_namespace_to_use = st.session_state.get(
        "selected_build_k8s_namespace", default_build_ns
    )
    st_object.caption(f"Build will target namespace: **{build_namespace_to_use}**")
    st_object.markdown("---")

    st_object.write(
        f"Provide source details to build and deploy a new {resource_type.lower()}."
    )
    source_url = st_object.text_input(
        f"{resource_type} Source Repository URL",
        value=constants.DEFAULT_REPO_URL,
        key=f"{resource_type.lower()}_source_url",
    )
    branch_or_tag = st_object.text_input(
        "Git Branch or Tag",
        value=constants.DEFAULT_REPO_BRANCH,
        key=f"{resource_type.lower()}_branch_or_tag",
    )
    selected_protocol = default_protocol
    if protocol_options:
        current_protocol_index = (
            protocol_options.index(default_protocol)
            if default_protocol in protocol_options
            else 0
        )
        selected_protocol = st_object.selectbox(
            "Select protocol:",
            options=protocol_options,
            index=current_protocol_index,
            key=f"selected_{resource_type.lower()}_protocol_option",
        )
    selected_framework = default_framework
    final_source_subfolder_path = ""
    if source_url and branch_or_tag:
        st_object.markdown("---")
        st_object.subheader("Specify Source Subfolder")
        subfolder_selection_method = st_object.radio(
            "Subfolder specification:",
            ("Select from examples", "Enter manually"),
            key=f"{resource_type.lower()}_subfolder_method",
        )
        if subfolder_selection_method == "Select from examples":
            if example_subfolders:  # Check if example_subfolders is not empty
                selected_example = st_object.selectbox(
                    "Select an example:",
                    options=[""] + example_subfolders,
                    key=f"selected_{resource_type.lower()}_example_subfolder",
                    format_func=lambda x: x if x else "Select an example...",
                )
                if selected_example:
                    final_source_subfolder_path = selected_example
            else:
                st_object.info("No example subfolders.")
        manual_subfolder_input = st_object.text_input(
            "Source Subfolder Path (relative to root)",
            value=final_source_subfolder_path if final_source_subfolder_path else "",
            placeholder=f"e.g., {resource_type.lower()}s/my-new-{resource_type.lower()}",
            key=f"manual_{resource_type.lower()}_source_subfolder_path",
        )
        if manual_subfolder_input:
            final_source_subfolder_path = manual_subfolder_input

    if st_object.button(
        f"Build New {resource_type}", key=f"build_new_{resource_type.lower()}_btn"
    ):
        resource_name_suggestion = get_resource_name_from_path(
            final_source_subfolder_path
        )
        if not all(
            [
                source_url,
                branch_or_tag,
                final_source_subfolder_path,
                resource_name_suggestion,
                build_namespace_to_use,
            ]
        ):
            st_object.warning(
                "Please provide all source details, subfolder path, and select a build namespace."
            )
            return
        if (
            not k8s_api_client
        ):
            st_object.error(
                "Kubernetes client is not available. Cannot proceed with build. Please check K8s connection status at the top."
            )
            return

        custom_obj_api = get_custom_objects_api()
        core_v1_api = get_core_v1_api()
        if not custom_obj_api or not core_v1_api:
            st_object.error(
                "Kubernetes API clients (CustomObjects or CoreV1) not initialized correctly. Cannot trigger build."
            )
            return

        trigger_and_monitor_build(
            st_object=st,
            custom_obj_api=custom_obj_api,
            core_v1_api=core_v1_api,
            build_namespace=build_namespace_to_use,
            resource_name_suggestion=resource_name_suggestion,
            resource_type=resource_type.lower(),
            repo_url=source_url,
            repo_branch=branch_or_tag,
            source_subfolder=final_source_subfolder_path,
            protocol=selected_protocol,
            framework=selected_framework,
            description=f"{resource_type} '{resource_name_suggestion}' built from UI in namespace {build_namespace_to_use}.",
        )
    st_object.markdown("---")
