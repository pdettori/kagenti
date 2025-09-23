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

from pathlib import Path
from kubernetes import client
import typer
from .. import config
from ..utils import run_command, get_api_client, console
from ..ocp_utils import verify_operator_installation

def install(use_openshift_cluster: bool = False, **kwargs):
    if use_openshift_cluster:
        _install_on_openshift()
    else:
        _install_on_k8s()

def _install_on_k8s():
    """Installs Tekton Pipelines from its official release YAML."""
    tekton_url = f"https://storage.googleapis.com/tekton-releases/pipeline/previous/{config.TEKTON_VERSION}/release.yaml"
    run_command(
        ["kubectl", "apply", "--filename", tekton_url], "Installing Tekton Pipelines"
    )

def _install_on_openshift():
    """Installs Tekton Pipelines using OpenShift Pipelines Operator."""
    namespace = "openshift-operators"
    subscription = "openshift-pipelines-operator-rh"
    deploy_path: Path = config.RESOURCES_DIR / "ocp" / "openshift-pipelines-operator.yaml"
    run_command(
        ["kubectl", "apply", "-n", namespace, "-f", deploy_path],
        "Installing OpenShift Pipelines operator"
    )

    try:
        custom_obj_api = get_api_client(client.CustomObjectsApi)
    except Exception as e:
        console.log(
                f"[bold red]✗ Could not connect to Kubernetes: {e}[/bold red]"
            )
        raise typer.Exit(1)
    
    verify_operator_installation(
        custom_obj_api,
        subscription_name=subscription,
        namespace=namespace,
    )

    