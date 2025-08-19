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

from .. import config
from ..utils import run_command


def install():

    """Deploy Envoy Gateway CRDs."""
    # This command sets up Envoy Gateway CRDs
    run_command(
        [
            "kubectl",
            "apply",
            "-k",
            "https://github.com/kubernetes-sigs/gateway-api/config/crd?ref=v1.3.0",
        ],
        "Installing Envoy Gateway CRDs",
    )

    """Deploy Envoy Gateway control-plane."""
    # This command installs or upgrades Envoy Gateway control-plane (idempotent)
    run_command(
        [
            "helm",
            "upgrade",
            "--install",
            "eg",
            "oci://docker.io/envoyproxy/gateway-helm",
            "--version",
            "v1.4.1",
            "-n",
            "envoy-gateway-system",
            "--create-namespace",
        ],
        "Deploy Envoy Gateway control-plane",
    )

    """Deploy Envoy Gateway data-plane."""
    # This command installs Envoy Gateway data-plane
    run_command(
        ["kubectl", "apply", "-f", str(config.RESOURCES_DIR / "gateway.yaml")],
        "Deploy Envoy Gateway data-plane",
    )

    """Deploy Envoy Gateway EnvoyProxy CR."""
    # This command installs Envoy Gateway EnvoyProxy CR
    run_command(
        ["kubectl", "apply", "-f", str(config.RESOURCES_DIR / "envoyproxy.yaml")],
        "Deploy Envoy Gateway EnvoyProxy CR",
    )

    """Deploy Envoy Gateway helper."""
    # This command installs Envoy Gateway helper
    run_command(
        ["kubectl", "apply", "-f", str(config.RESOURCES_DIR / "gateway-helper.yaml")],
        "Deploy Envoy Gateway helper",
    )

    """Deploy Envoy Gateway WASM filter."""
    # This command installs Envoy Gateway WASM filter
    run_command(
        ["kubectl", "apply", "-f", str(config.RESOURCES_DIR / "wasm-filter.yaml")],
        "Deploy Envoy Gateway WASM filter",
    )
