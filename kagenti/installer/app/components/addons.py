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
import typer
from kubernetes import client
from .. import config
from ..utils import run_command, get_api_client, console
from ..ocp_utils import verify_operator_installation


def install(
    use_openshift_cluster: bool = False, use_existing_cluster: bool = False, **kwargs
):
    """Installs Prometheus, Kiali, Phoenix, and the OpenTelemetry Collector."""
    # Prometheus
    run_command(
        [
            "kubectl",
            "apply",
            "-f",
            "https://raw.githubusercontent.com/istio/istio/release-1.25/samples/addons/prometheus.yaml",
        ],
        "Installing Prometheus",
    )
    run_command(
        ["kubectl", "rollout", "status", "-n", "istio-system", "deployment/prometheus"],
        "Waiting for Prometheus rollout",
    )

    # Kiali
    if use_openshift_cluster:
        operator_path: Path = config.RESOURCES_DIR / "ocp" / "kiali-operator.yaml"
        namespace = "openshift-operators"
        subscription = "kiali-ossm"
        run_command(
            ["kubectl", "apply", "-n", namespace, "-f", operator_path],
            "Installing Kiali Operator",
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

        # apply kiali config
        config_path: Path = config.RESOURCES_DIR / "ocp" / "kiali-config.yaml"
        run_command(["kubectl", "apply", "-f", config_path], "Configuring Kiali")
    else:
        run_command(
            [
                "kubectl",
                "apply",
                "-f",
                "https://raw.githubusercontent.com/istio/istio/release-1.25/samples/addons/kiali.yaml",
            ],
            "Installing Kiali",
        )
        run_command(
            ["kubectl", "apply", "-f", str(config.RESOURCES_DIR / "kiali-route.yaml")],
            "Adding Kiali Route",
        )
        run_command(
            [
                "kubectl",
                "label",
                "ns",
                "istio-system",
                "shared-gateway-access=true",
                "--overwrite",
            ],
            "Enabling istio-system for kiali routing",
        )
        run_command(
            ["kubectl", "rollout", "status", "-n", "istio-system", "deployment/kiali"],
            "Waiting for Kiali rollout",
        )

    # Phoenix & Postgres
    run_command(
        [
            "kubectl",
            "apply",
            "-n",
            "kagenti-system",
            "-f",
            str(config.RESOURCES_DIR / "phoenix.yaml"),
        ],
        "Installing Phoenix",
    )
    run_command(
        [
            "kubectl",
            "rollout",
            "status",
            "-n",
            "kagenti-system",
            "statefulset/postgres",
        ],
        "Waiting for Postgres rollout",
    )
    run_command(
        ["kubectl", "rollout", "status", "-n", "kagenti-system", "statefulset/phoenix"],
        "Waiting for Phoenix rollout",
    )

    # OpenTelemetry Collector
    run_command(
        [
            "kubectl",
            "apply",
            "-n",
            "kagenti-system",
            "-f",
            str(config.RESOURCES_DIR / "otel-collector.yaml"),
        ],
        "Installing Otel Collector",
    )
    run_command(
        [
            "kubectl",
            "rollout",
            "status",
            "-n",
            "kagenti-system",
            "deployment/otel-collector",
        ],
        "Waiting for otel collector rollout",
    )
    if use_openshift_cluster:
        run_command(
            [
                "kubectl",
                "apply",
                "-f",
                str(config.RESOURCES_DIR / "ocp" / "phoenix-route.yaml"),
            ],
            "Setting up Phoenix Route",
        )
