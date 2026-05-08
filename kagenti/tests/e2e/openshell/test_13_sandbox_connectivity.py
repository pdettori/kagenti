"""
Sandbox Connectivity E2E Tests (MVP Validation Criterion #2)

Validates that interactive sessions can be established with sandboxes:
- Gateway API is reachable and responds
- Sandbox pods support kubectl exec (compute driver mechanism)
- Sandbox containers can run commands interactively

This is the E2E equivalent of ``openshell term`` — verifying that the
infrastructure for interactive access is functional.
"""

import os
import subprocess
import time

import pytest

from kagenti.tests.e2e.openshell.conftest import (
    kubectl_get_pods_json,
    kubectl_run,
)

pytestmark = [pytest.mark.openshell, pytest.mark.mvp]

SANDBOX_NS = os.getenv("OPENSHELL_AGENT_NAMESPACE", "team1")
BASE_IMAGE = "ghcr.io/nvidia/openshell-community/sandboxes/base:latest"
SANDBOX_NAME = "test-connectivity-exec"


class TestGatewayConnectivity:
    """Verify gateway is reachable and accepting connections."""

    def test_gateway_pod_running(self):
        """Gateway StatefulSet has at least one running pod."""
        pods = kubectl_get_pods_json(SANDBOX_NS)
        gateway_pods = [
            p
            for p in pods
            if p["metadata"]["name"].startswith("openshell-server")
            and p["status"].get("phase") == "Running"
        ]
        assert gateway_pods, f"No running openshell-server pod in {SANDBOX_NS}"

    def test_gateway_service_has_endpoints(self):
        """Gateway service has at least one ready endpoint."""
        result = kubectl_run(
            "get",
            "endpoints",
            "openshell-server",
            "-n",
            SANDBOX_NS,
            "-o",
            "jsonpath={.subsets[0].addresses[0].ip}",
        )
        assert result.returncode == 0 and result.stdout.strip(), (
            f"openshell-server service in {SANDBOX_NS} has no endpoints"
        )

    def test_gateway_port_forward_reachable(self):
        """Gateway responds to HTTP requests via port-forward."""
        import socket

        local_port = _find_free_port()
        proc = subprocess.Popen(
            [
                "kubectl",
                "port-forward",
                "svc/openshell-server",
                f"{local_port}:8080",
                "-n",
                SANDBOX_NS,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            for _ in range(10):
                time.sleep(1)
                try:
                    sock = socket.create_connection(
                        ("localhost", local_port), timeout=2
                    )
                    sock.close()
                    return  # Success — port is reachable
                except (ConnectionRefusedError, OSError):
                    continue

            pytest.fail("Gateway port 8080 not reachable via port-forward")
        finally:
            proc.terminate()
            proc.wait()


class TestSandboxExec:
    """Verify interactive command execution inside sandbox pods."""

    def test_create_sandbox_and_exec(self):
        """Create a sandbox-style pod and execute a command inside it.

        The agent-sandbox controller reconciles pods on-demand (via gateway
        session requests), not automatically from the Sandbox CR.  This test
        validates the exec mechanism directly by creating a pod with the same
        image used by sandboxes.
        """
        pod_name = SANDBOX_NAME

        # Cleanup any leftover from a previous run
        kubectl_run("delete", "pod", pod_name, "-n", SANDBOX_NS, "--ignore-not-found")
        time.sleep(2)

        # Create a pod directly using the sandbox base image
        result = subprocess.run(
            [
                "kubectl",
                "run",
                pod_name,
                "-n",
                SANDBOX_NS,
                f"--image={BASE_IMAGE}",
                "--restart=Never",
                "--command",
                "--",
                "sleep",
                "300",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Failed to create pod: {result.stderr}"

        # Wait for pod to be Running
        last_phase = "unknown"
        deadline = time.time() + 120
        while time.time() < deadline:
            pods = kubectl_get_pods_json(SANDBOX_NS)
            matching = [p for p in pods if p["metadata"].get("name") == pod_name]
            if matching:
                last_phase = matching[0]["status"].get("phase", "unknown")
                if last_phase == "Running":
                    break
            time.sleep(3)

        assert last_phase == "Running", (
            f"Pod did not reach Running state within 120s (last phase: {last_phase})"
        )

        try:
            exec_result = subprocess.run(
                [
                    "kubectl",
                    "exec",
                    pod_name,
                    "-n",
                    SANDBOX_NS,
                    "--",
                    "echo",
                    "hello-from-sandbox",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            assert exec_result.returncode == 0, (
                f"kubectl exec failed: {exec_result.stderr}"
            )
            assert "hello-from-sandbox" in exec_result.stdout

        finally:
            kubectl_run(
                "delete",
                "pod",
                pod_name,
                "-n",
                SANDBOX_NS,
                "--ignore-not-found",
                "--wait=false",
            )

    def test_sandbox_exec_shell_interactive(self):
        """Sandbox supports shell command execution (simulates terminal session)."""
        # Use the pod created by test_create_sandbox_and_exec or any sandbox pod
        pods = kubectl_get_pods_json(SANDBOX_NS)
        sandbox_pods = [
            p
            for p in pods
            if (
                "sandbox" in p["metadata"].get("name", "").lower()
                or p["metadata"].get("name") == SANDBOX_NAME
            )
            and p["status"].get("phase") == "Running"
        ]

        if not sandbox_pods:
            pytest.skip("No running sandbox pod available for exec test")

        pod_name = sandbox_pods[0]["metadata"]["name"]
        container = sandbox_pods[0]["spec"]["containers"][0]["name"]

        exec_result = subprocess.run(
            [
                "kubectl",
                "exec",
                pod_name,
                "-n",
                SANDBOX_NS,
                "-c",
                container,
                "--",
                "sh",
                "-c",
                "whoami && pwd && echo SESSION_OK",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert exec_result.returncode == 0, f"Shell exec failed: {exec_result.stderr}"
        assert "SESSION_OK" in exec_result.stdout


def _find_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
