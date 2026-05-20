"""
T7.1 Teleport Tests

Validates session teleporting — packaging local context into a sandbox,
executing prompts with context, and cleanup.

Tests are assertive: if infrastructure is deployed, they MUST pass.
"""

import os
import subprocess

import pytest

from kagenti.tests.e2e.openshell.conftest import (
    kubectl_run,
    sandbox_crd_installed,
)

pytestmark = [pytest.mark.openshell]

TELEPORT_NS = os.getenv("OPENSHELL_AGENT_NAMESPACE", "team1")
LLM_AVAILABLE = os.getenv("OPENSHELL_LLM_AVAILABLE", "").lower() == "true"

skip_no_crd = pytest.mark.skipif(
    not sandbox_crd_installed(), reason="Sandbox CRD not installed"
)
skip_no_llm = pytest.mark.skipif(not LLM_AVAILABLE, reason="LLM not available")


def _teleport_script() -> str:
    repo_root = os.getenv(
        "REPO_ROOT",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."),
    )
    script = os.path.join(repo_root, "scripts", "openshell", "teleport-session.sh")
    assert os.path.isfile(script), f"teleport-session.sh not found at {script}"
    return script


def _run_teleport(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_teleport_script(), *args, "--namespace", TELEPORT_NS],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _gateway_running() -> bool:
    result = kubectl_run(
        "get",
        "pods",
        "-n",
        TELEPORT_NS,
        "-l",
        "app.kubernetes.io/name=openshell",
        "--no-headers",
    )
    return result.returncode == 0 and "Running" in result.stdout


class TestTeleportPackage:
    """Package and cleanup — no sandbox pod needed."""

    @skip_no_crd
    def test_teleport__package_creates_configmap(self):
        """Packaging creates a ConfigMap with CLAUDE.md content."""
        result = _run_teleport("--package")
        assert result.returncode == 0, f"Package failed: {result.stderr}"

        session_id = result.stdout.strip().split("\n")[-1]
        assert len(session_id) == 8, f"Expected 8-char session ID, got: {session_id}"

        cm_name = f"teleport-ctx-{session_id}"
        check = kubectl_run("get", "configmap", cm_name, "-n", TELEPORT_NS)
        assert check.returncode == 0, f"ConfigMap {cm_name} not found"

        _run_teleport("--cleanup", "--session", session_id)

    @skip_no_crd
    def test_teleport__cleanup_removes_resources(self):
        """Cleanup deletes ConfigMap."""
        result = _run_teleport("--package")
        assert result.returncode == 0
        session_id = result.stdout.strip().split("\n")[-1]

        _run_teleport("--cleanup", "--session", session_id)

        cm = kubectl_run(
            "get", "configmap", f"teleport-ctx-{session_id}", "-n", TELEPORT_NS
        )
        assert cm.returncode != 0, "ConfigMap should be deleted after cleanup"

    def test_teleport__script_exists(self):
        """Teleport script exists and is executable."""
        script = _teleport_script()
        assert os.access(script, os.X_OK), f"{script} is not executable"


class TestTeleportLifecycle:
    """Full lifecycle in a single sandbox: deploy, verify context, prompt, cleanup."""

    @skip_no_crd
    def test_teleport__full_lifecycle(self):
        """Deploy sandbox, verify context is unpacked, cleanup."""
        if not _gateway_running():
            pytest.fail("OpenShell gateway not running — compute driver required")

        # Step 1: Package
        result = _run_teleport("--package")
        assert result.returncode == 0, f"Package failed: {result.stderr}"
        session_id = result.stdout.strip().split("\n")[-1]

        try:
            # Step 2: Deploy (creates pod + unpacks context)
            deploy = _run_teleport("--deploy", "--session", session_id, timeout=120)
            assert deploy.returncode == 0, (
                f"Deploy failed:\nstdout: {deploy.stdout[-500:]}\n"
                f"stderr: {deploy.stderr[-500:]}"
            )

            # Step 3: Verify context unpacked
            sb_name = f"teleport-{session_id}"
            pods = kubectl_run("get", "pods", "-n", TELEPORT_NS, "--no-headers")
            pod_name = ""
            for line in pods.stdout.strip().split("\n"):
                if sb_name in line and "Running" in line:
                    pod_name = line.split()[0]
                    break
            assert pod_name, f"No running pod matching {sb_name}"

            check = kubectl_run(
                "exec",
                pod_name,
                "-n",
                TELEPORT_NS,
                "-c",
                "sandbox",
                "--",
                "sh",
                "-c",
                "cat $HOME/CLAUDE.md",
                timeout=15,
            )
            assert check.returncode == 0, (
                f"CLAUDE.md not found in sandbox $HOME.\n"
                f"Check: kubectl exec {pod_name} -n {TELEPORT_NS} "
                f"-c sandbox -- sh -c 'ls -la $HOME/ && id'\n"
                f"stderr: {check.stderr}"
            )
            assert "Kagenti" in check.stdout, (
                f"CLAUDE.md doesn't mention Kagenti: {check.stdout[:200]}"
            )

        finally:
            _run_teleport("--cleanup", "--session", session_id)

    @skip_no_crd
    @skip_no_llm
    def test_teleport__prompt_with_context(self):
        """Deploy sandbox, send prompt that reads CLAUDE.md, verify response."""
        if not _gateway_running():
            pytest.fail("OpenShell gateway not running — compute driver required")

        result = _run_teleport("--package")
        assert result.returncode == 0
        session_id = result.stdout.strip().split("\n")[-1]

        try:
            deploy = _run_teleport("--deploy", "--session", session_id, timeout=120)
            assert deploy.returncode == 0, f"Deploy failed: {deploy.stderr[-300:]}"

            prompt = _run_teleport(
                "--session",
                session_id,
                "--prompt",
                "What is the name of the project described in CLAUDE.md? "
                "Reply with just the project name, nothing else.",
                timeout=180,
            )
            assert prompt.returncode == 0, f"Prompt failed: {prompt.stderr[-300:]}"

            output = prompt.stdout.strip()
            assert len(output) > 0, "Empty response from teleported session"
            assert any(
                term in output.lower() for term in ["kagenti", "agent", "platform"]
            ), f"Response doesn't reference the project: {output[:200]}"

        finally:
            _run_teleport("--cleanup", "--session", session_id)
