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

import kubernetes.client
import kubernetes.config


def load_kube_config(st):
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


def is_deployment_ready(data):
    """
    helper to parse the Agent object and get status from conditions
    """
    conditions = data.get("status", {}).get("conditions", [])
    for condition in conditions:
        if condition.get("reason") == "DeploymentReady" and \
           condition.get("type") == "Ready" and \
           condition.get("status") == "True":
            return "Ready"
    return "Unknown"

def list_agents(st, api_instance, namespace="default"):
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

def get_agent_details(st, api_instance, agent_name: str, namespace="default"):
    """
    Fetches details for a specific 'Agent' custom resource.
    """
    group = "beeai.beeai.dev"
    version = "v1"
    plural = "agents"

    try:
        agent_obj = api_instance.get_namespaced_custom_object(group, version, namespace, plural, agent_name)
        return agent_obj
    except kubernetes.client.ApiException as e:
        if e.status == 404:
            st.warning(f"Agent '{agent_name}' not found in namespace '{namespace}'.")
        elif e.status == 403:
            st.warning("Permission denied. Ensure your Kubernetes user/service account has 'get' permissions on 'agents.beeai.beeai.dev'.")
        else:
            st.error(f"Error fetching details for agent '{agent_name}': {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

