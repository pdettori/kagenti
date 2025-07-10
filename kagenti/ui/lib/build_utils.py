# Assisted by watsonx Code Assistant
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
import logging
import json
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
    get_config_map_data,
    _handle_kube_api_exception,
    _display_kube_config_status_once,
)
from .utils import sanitize_for_k8s_name, remove_url_prefix, get_resource_name_from_path
import logging

logger = logging.getLogger(__name__)


def _get_keycloak_client_secret(st_object, client_name: str) -> str:
    """
    Retrieves the client secret from Keycloak for the given client name.

    Args:
        st_object (streamlit.elements.StreamlitElement): The Streamlit object to display messages.
        client_name (str): The name of the Keycloak client.

    Returns:
        str: The client secret if found, otherwise an empty string.
    """
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


def _construct_tool_resource_body(
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
    """
    Constructs the Kubernetes resource body for a new build.

    Args:
        st_object (streamlit.elements.StreamlitElement): The Streamlit object to display messages.
        core_v1_api (kubernetes.client.CoreV1Api): The Kubernetes CoreV1 API client.
        build_namespace (str): The namespace where the build will be created.
        resource_name (str): The name of the resource to be built.
        resource_type (str): The type of the resource (e.g., Agent, Tool).
        repo_url (str): The URL of the Git repository.
        repo_branch (str): The Git branch or tag to use for the build.
        source_subfolder (str): The subfolder in the repository to use for the build.
        protocol (str): The protocol to use for the resource.
        framework (str): The framework to use for the resource.
        description (str): A description for the resource.
        additional_env_vars (Optional[list]): Additional environment variables to include in the build.
        image_tag (str): The image tag to use for the build.

    Returns:
        Optional[dict]: The constructed Kubernetes resource body, or None if an error occurred.
    """
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
    #image_registry_prefix = f"ghcr.io/{repo_user}"
    image_registry_prefix = f"registry.cr-system.svc.cluster.local:5000"
    client_secret_for_env = _get_keycloak_client_secret(
        st_object, f"{k8s_resource_name}-client"
    )
    final_env_vars = list(constants.DEFAULT_ENV_VARS)
    if additional_env_vars:
        final_env_vars.extend(additional_env_vars)
    if client_secret_for_env:
        final_env_vars.append({"name": "CLIENT_SECRET", "value": client_secret_for_env})
    
    # Build the spec dictionary
    spec = {
        "suspend": False,
        "tool": {
            "toolType": "MCP",
            "build": {
                "mode": "dev",
                "pipeline": {
                    "parameters": [
                        {
                            "name": "SOURCE_REPO_SECRET",
                            "value": "github-token-secret",
                        },
                        {
                            "name": "repo-url",
                            "value": remove_url_prefix(repo_url),
                        },
                        {
                            "name": "revision",
                            "value":  repo_branch,
                        },
                        {
                            "name": "subfolder-path",
                            "value": source_subfolder,
                        },
                        {
                            "name": "image",
                            "value":  f"{image_registry_prefix}/{image_name}:{image_tag}"
                        },
                    ], 
                "cleanupAfterBuild": True,    
                },
            },
        },
        "deployer": {
            "name": k8s_resource_name,
            "namespace": build_namespace,
            "deployAfterBuild": True,
            "kubernetes": {
                "imageSpec": {
                    "image": image_name,
                    "imageTag": image_tag,
                    "imageRegistry": image_registry_prefix,
                    "imagePullPolicy": "IfNotPresent",
                },
                "containerPorts": [
                    {
                        "name": "http",
                        "containerPort": constants.DEFAULT_IN_CLUSTER_PORT,
                        "protocol": "TCP",
                    },
                ],
                "servicePorts": [
                    {
                        "name": "http",
                        "port": constants.DEFAULT_IN_CLUSTER_PORT,
                        "targetPort": constants.DEFAULT_IN_CLUSTER_PORT,
                        "protocol": "TCP",
                    },
                ],
                "resources": {
                    "limits": constants.DEFAULT_RESOURCE_LIMITS,
                    "requests": constants.DEFAULT_RESOURCE_REQUESTS,
                },    
                
            },
            "env": final_env_vars,
        },
    }
        
    body = {
        "apiVersion": f"{constants.CRD_GROUP}/{constants.CRD_VERSION}",
        "kind": "Component",
        "metadata": {
            "name": k8s_resource_name,
            "namespace": constants.OPERATOR_NS,
            "labels": {
                constants.APP_KUBERNETES_IO_CREATED_BY: constants.STREAMLIT_UI_CREATOR_LABEL,
                constants.APP_KUBERNETES_IO_NAME: constants.KAGENTI_OPERATOR_LABEL_NAME,
                constants.KAGENTI_TYPE_LABEL: resource_type,
                constants.KAGENTI_PROTOCOL_LABEL: protocol,
                constants.KAGENTI_FRAMEWORK_LABEL: framework,
            },
        },
        "spec": spec,
    }
    return body


def _construct_agent_resource_body(
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
    """
    Constructs the Kubernetes resource body for a new build.

    Args:
        st_object (streamlit.elements.StreamlitElement): The Streamlit object to display messages.
        core_v1_api (kubernetes.client.CoreV1Api): The Kubernetes CoreV1 API client.
        build_namespace (str): The namespace where the build will be created.
        resource_name (str): The name of the resource to be built.
        resource_type (str): The type of the resource (e.g., Agent, Tool).
        repo_url (str): The URL of the Git repository.
        repo_branch (str): The Git branch or tag to use for the build.
        source_subfolder (str): The subfolder in the repository to use for the build.
        protocol (str): The protocol to use for the resource.
        framework (str): The framework to use for the resource.
        description (str): A description for the resource.
        additional_env_vars (Optional[list]): Additional environment variables to include in the build.
        image_tag (str): The image tag to use for the build.

    Returns:
        Optional[dict]: The constructed Kubernetes resource body, or None if an error occurred.
    """
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
    image_registry_prefix = f"registry.cr-system.svc.cluster.local:5000"
    client_secret_for_env = _get_keycloak_client_secret(
        st_object, f"{k8s_resource_name}-client"
    )
    final_env_vars = list(constants.DEFAULT_ENV_VARS)
    if additional_env_vars:
        final_env_vars.extend(additional_env_vars)
    if client_secret_for_env:
        final_env_vars.append({"name": "CLIENT_SECRET", "value": client_secret_for_env})
    body = {
        "apiVersion": f"{constants.CRD_GROUP}/{constants.CRD_VERSION}",
        "kind": "Component",
        "metadata": {
            "name": k8s_resource_name,
            "namespace": constants.OPERATOR_NS,
            "labels": {
                constants.APP_KUBERNETES_IO_CREATED_BY: constants.STREAMLIT_UI_CREATOR_LABEL,
                constants.APP_KUBERNETES_IO_NAME: constants.KAGENTI_OPERATOR_LABEL_NAME,
                constants.KAGENTI_TYPE_LABEL: resource_type,
                constants.KAGENTI_PROTOCOL_LABEL: protocol,
                constants.KAGENTI_FRAMEWORK_LABEL: framework,
            },
        },
        "spec": {
            "suspend": False,
            "agent": {
                "build": {
                    "mode": "dev",
                    "pipeline": {
                        "parameters": [
                            {
                                "name": "SOURCE_REPO_SECRET",
                                "value": "github-token-secret",
                            },
                            {
                                "name": "repo-url",
                                "value": remove_url_prefix(repo_url),
                            },
                            {
                                "name": "revision",
                                "value":  repo_branch,
                            },
                            {
                                "name": "subfolder-path",
                                "value": source_subfolder,
                            },
                            {
                                "name": "image",
                                "value":  f"{image_registry_prefix}/{image_name}:{image_tag}"
                            },
                        ], 
                    "cleanupAfterBuild": True,    
                    },
                },
            },
            "deployer": {
                "name": k8s_resource_name,
                "namespace": build_namespace,
                "deployAfterBuild": True,
                "kubernetes": {
                    "imageSpec": {
                        "image": image_name,
                        "imageTag": image_tag,
                        "imageRegistry": image_registry_prefix,
                        "imagePullPolicy": "IfNotPresent",
                    },
                    "containerPorts": [
                        {
                            "name": "http",
                            "containerPort": constants.DEFAULT_IN_CLUSTER_PORT,
                            "protocol": "TCP",
                        },
                    ],
                    "servicePorts": [
                        {
                            "name": "http",
                            "port": constants.DEFAULT_IN_CLUSTER_PORT,
                            "targetPort": constants.DEFAULT_IN_CLUSTER_PORT,
                            "protocol": "TCP",
                        },
                    ],
                    "resources": {
                        "limits": constants.DEFAULT_RESOURCE_LIMITS,
                        "requests": constants.DEFAULT_RESOURCE_REQUESTS,
                    },    
                    
                },
                "env": final_env_vars,
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
    additional_env_vars: Optional[List[Dict[str, Any]]] = None,
):
    """
    Triggers a build for a new resource and monitors its status.

    Args:
        st_object (streamlit.elements.StreamlitElement): The Streamlit object to display messages.
        custom_obj_api (kubernetes.client.CustomObjectsApi): The Kubernetes CustomObjects API client.
        core_v1_api (kubernetes.client.CoreV1Api): The Kubernetes CoreV1 API client.
        build_namespace (str): The namespace where the build will be created.
        resource_name_suggestion (str): The suggested name for the new resource.
        resource_type (str): The type of the resource (e.g., Agent, Tool).
        repo_url (str): The URL of the Git repository.
        repo_branch (str): The Git branch or tag to use for the build.
        source_subfolder (str): The subfolder in the repository to use for the build.
        protocol (str): The protocol to use for the resource.
        framework (str): The framework to use for the resource.
        description (str): A description for the resource.
        additional_env_vars (Optional[List[Dict[str, Any]]]): Additional environment variables to include in the build.

    Returns:
        bool: True if the build was successful, False otherwise.
    """
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
    logger.info(f"Generating Component manifest\n")
    k8s_resource_name = sanitize_for_k8s_name(resource_name_suggestion)
    if not k8s_resource_name:
        st_object.error("Invalid resource name after sanitization. Cannot proceed.")
        return False
    if resource_type.lower() == "agent":
        build_cr_body = _construct_agent_resource_body(
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
           additional_env_vars=additional_env_vars,
        )
    elif resource_type.lower() == "tool":
        build_cr_body = _construct_tool_resource_body(
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
           additional_env_vars=additional_env_vars,
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

            logger.info(f"Generated Component manifest:\n%s", json.dumps(build_cr_body, indent=2))
            custom_obj_api.create_namespaced_custom_object(
                group=constants.CRD_GROUP,
                version=constants.CRD_VERSION,
                namespace=constants.OPERATOR_NS,
                plural=constants.COMPONENTS_PLURAL,
                body=build_cr_body,
            )
            st_object.success(
                f"{resource_type.capitalize()} '{k8s_resource_name}' creation request sent to namespace '{build_namespace}'."
            )
        except kubernetes.client.ApiException as e:
            _handle_kube_api_exception(
                st_object,
                e,
                f"{resource_type.capitalize()} '{k8s_resource_name}'",
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
            current_build_status not in ["Succeeded", "Failed", "Error"]
            and retries < max_retries
        ):
            retries += 1
            try:
                build_obj = custom_obj_api.get_namespaced_custom_object(
                    group=constants.CRD_GROUP,
                    version=constants.CRD_VERSION,
                    namespace=constants.OPERATOR_NS,
                    plural=constants.COMPONENTS_PLURAL,
                    name=k8s_resource_name,
                )
                status_data = build_obj.get("status", {})
                #current_build_status = status_data.get("buildStatus", "Unknown")
                build_status_data = status_data.get("buildStatus", {})
                current_build_status = build_status_data.get("phase", "Unknown")

                status_message = build_status_data.get("message", "")
                #deployment_status = status_data.get("deploymentStatus", "")
                deployment_status_data = status_data.get("deploymentStatus", {})
                deployment_phase = deployment_status_data.get("phase", "Unknown")

                status_placeholder.info(
                    f"Build Status for '{k8s_resource_name}': **{current_build_status}**\nMessage: {status_message}\nDeployment Status: **{deployment_phase}**"
                )
                if current_build_status in ["Succeeded", "Failed", "Error"]:
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
            "Succeeded",
            "Failed",
            "Error",
        ]:
            status_placeholder.error(
                f"Timeout waiting for build of '{k8s_resource_name}' to complete."
            )
            return False
        
    if current_build_status == "Succeeded":
        # Now wait for deployment to complete
        deployment_retries = 0
        max_deployment_retries = 120
        final_deployment_phase = "Unknown"
    
        with st_object.spinner(
           f"Build succeeded. Waiting for {resource_type} '{k8s_resource_name}' to deploy..."
        ):
           while (
              final_deployment_phase not in ["Ready", "Failed", "Error"]
              and deployment_retries < max_deployment_retries
            ):
                deployment_retries += 1
                try:
                   # Re-fetch the object to get latest deployment status
                    build_obj = custom_obj_api.get_namespaced_custom_object(
                      group=constants.CRD_GROUP,
                      version=constants.CRD_VERSION,
                      namespace=constants.OPERATOR_NS,
                      plural=constants.COMPONENTS_PLURAL,
                      name=k8s_resource_name,
                    )
                
                    final_deployment_status = build_obj.get("status", {}).get(
                       "deploymentStatus", {}
                    )
                    final_deployment_phase = final_deployment_status.get("phase", "Unknown")
                    deployment_message = final_deployment_status.get("deploymentMessage", "")
                
                    # Update status display
                    status_placeholder.info(
                       f"Deployment Status for '{k8s_resource_name}': **{final_deployment_phase}**\n"
                       f"Message: {deployment_message}"
                    )
                
                    if final_deployment_phase in ["Ready", "Failed", "Error"]:
                       break
                    
                    time.sleep(constants.POLL_INTERVAL_SECONDS)
                
                except Exception as e:
                   st_object.warning(f"Error checking deployment status: {str(e)}")
                   time.sleep(constants.POLL_INTERVAL_SECONDS)
    
        # Handle final deployment status
        if final_deployment_phase == "Ready":
            st_object.success(
               f"{resource_type.capitalize()} '{k8s_resource_name}' built and deployed successfully in namespace '{build_namespace}'!"
            )
            return True
        elif final_deployment_phase in ["Failed", "Error"]:
            st_object.error(
              f"{resource_type.capitalize()} '{k8s_resource_name}' deployment failed with status: {final_deployment_phase}. Check operator logs."
            )
            return False
        else:
           # Timeout case
            st_object.warning(
               f"{resource_type.capitalize()} '{k8s_resource_name}' deployment timed out after {max_deployment_retries} attempts. "
               f"Last status: {final_deployment_phase}. Manual check might be needed."
            )
            return False
        
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
    """
    Renders the common UI form for importing a new Agent or Tool.

    Args:
        st_object (streamlit.elements.StreamlitElement): The Streamlit object to display messages.
        resource_type (str): The type of the resource (e.g., Agent, Tool).
        default_protocol (str): The default protocol for the resource.
        default_framework (str): The default framework for the resource.
        k8s_api_client (Optional[kubernetes.client.ApiClient]): The Kubernetes API client.
        k8s_client_status_msg (Optional[str]): The message to display for the Kubernetes client status.
        k8s_client_status_icon (Optional[str]): The icon to display for the Kubernetes client status.
        example_subfolders (List[str]): The list of example subfolders.
        protocol_options (Optional[List[str]]): The list of available protocols.
    """
    st_object.header(f"Import New {resource_type}")

    _display_kube_config_status_once(
        k8s_client_status_msg, k8s_client_status_icon, bool(k8s_api_client)
    )

    core_v1_api = get_core_v1_api()

    # --- Namespace Selector for Build/Deployment ---
    available_build_namespaces = ["default"]
    if k8s_api_client:
        available_build_namespaces = get_all_namespaces(k8s_api_client)
        if not available_build_namespaces:
            available_build_namespaces = ["default"]
            st_object.caption(
                "Could not list all namespaces, defaulting to 'default'. Check K8s permissions."
            )
    else:
        st_object.caption(
            "Kubernetes client not available. Build will target 'default' namespace."
        )

    default_build_ns = "default"
    initial_selected_build_ns = st.session_state.get(
        "selected_build_k8s_namespace", default_build_ns
    )

    if initial_selected_build_ns not in available_build_namespaces:
        initial_selected_build_ns = (
            default_build_ns
            if default_build_ns in available_build_namespaces
            else available_build_namespaces[0]
        )

    build_ns_index = available_build_namespaces.index(initial_selected_build_ns)

    newly_selected_build_namespace = st_object.selectbox(
        f"Select Namespace to Deploy {resource_type}:",
        options=available_build_namespaces,
        index=build_ns_index,
        key=f"{resource_type.lower()}_build_namespace_selector",
        help=f"The Component resource, the {resource_type}, and the '{constants.ENV_CONFIG_MAP_NAME}' ConfigMap will be in this namespace.",
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

    # --- Environment Variable Selection ---
    env_options = {}
    if core_v1_api:
        env_options = get_config_map_data(
            core_v1_api, build_namespace_to_use, constants.ENV_CONFIG_MAP_NAME
        )
        if env_options is None:
            env_options = {}

    selected_env_sets = []
    if env_options:
        st_object.subheader("Select Environment Variable Sets")
        sorted_env_keys = sorted(list(env_options.keys()))
        selected_env_sets = st_object.multiselect(
            "Select environments to append:",
            options=sorted_env_keys,
            key=f"{resource_type.lower()}_env_sets_selector",
            help=f"Select sets of environment variables from the '{constants.ENV_CONFIG_MAP_NAME}' ConfigMap in '{build_namespace_to_use}'.",
        )
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
            if example_subfolders:
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
        if not k8s_api_client:
            st_object.error(
                "Kubernetes client not available. Cannot proceed with build."
            )
            return

        final_additional_envs = []
        if selected_env_sets and env_options:
            for key in selected_env_sets:
                if key in env_options and isinstance(env_options[key], list):
                    final_additional_envs.extend(env_options[key])

        custom_obj_api = get_custom_objects_api()
        if not custom_obj_api or not core_v1_api:
            st_object.error(
                "K8s API clients not initialized correctly. Cannot trigger build."
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
            description=f"{resource_type} '{resource_name_suggestion}' built from UI.",
            additional_env_vars=final_additional_envs,
        )
    st_object.markdown("---")
