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

import typer

from pathlib import Path
from kubernetes import client, config
from .. import config
from ..utils import console, run_command, create_or_update_configmap, get_api_client
from ..ocp_utils import get_admitted_openshift_route_host

ALLOWED_ORIGINS_DEFAULT = "http://mcp-inspector.localtest.me:8080"
MCP_PROXY_FULL_ADDRESS_DEFAULT = "http://mcp-proxy.localtest.me:8080"
kagenti_namespace = "kagenti-system"


def install(use_openshift_cluster: bool = False, **kwargs):
    """Installs the MCP inspector"""

    allowed_origins = ALLOWED_ORIGINS_DEFAULT
    mcp_proxy_full_address = MCP_PROXY_FULL_ADDRESS_DEFAULT

    try:
        v1_api = get_api_client(client.CoreV1Api)
        custom_obj_api = get_api_client(client.CustomObjectsApi)
    except Exception as e:
        console.log(
            f"[bold red]✗ Could not connect to Kubernetes: {e}[/bold red]"
        )
        raise typer.Exit(1)

    if use_openshift_cluster:
        inspector_route_path: Path = (
            config.RESOURCES_DIR / "ocp" / "mcp-inspector-route.yaml"
        )
        run_command(
            ["kubectl", "apply", "-f", inspector_route_path],
            "Creating MCP Inspector Route",
        )
        allowed_origins = get_admitted_openshift_route_host(
            custom_obj_api,
            kagenti_namespace, "mcp-inspector"
        )

        proxy_route_path: Path = config.RESOURCES_DIR / "ocp" / "mcp-proxy-route.yaml"
        run_command(
            ["kubectl", "apply", "-f", proxy_route_path], "Creating MCP Proxy Route"
        )
        mcp_proxy_full_address = get_admitted_openshift_route_host(
            custom_obj_api,
            kagenti_namespace, "mcp-proxy"
        )

    # create configmap
    configmap = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=client.V1ObjectMeta(name="mcp-inspector-config", namespace=kagenti_namespace),
        data = {
            "ALLOWED_ORIGINS": allowed_origins,
            "MCP_PROXY_FULL_ADDRESS": mcp_proxy_full_address
        },
    )
    create_or_update_configmap(v1_api, "kagenti-system", configmap)

    deploy_path = str(config.RESOURCES_DIR / "mcp-inspector.yaml")
    run_command(
        ["kubectl", "apply", "-f", str(deploy_path)], "Installing MCP Inspector"
    )
    run_command(
        [
            "kubectl",
            "label",
            "ns",
            "kagenti-system",
            "shared-gateway-access=true",
            "--overwrite",
        ],
        "Sharing gateway access for inspector",
    )
    run_command(
        [
            "kubectl",
            "rollout",
            "status",
            "-n",
            "kagenti-system",
            "deployment/mcp-inspector",
        ],
        "Waiting for mcp-inspector rollout",
    )

