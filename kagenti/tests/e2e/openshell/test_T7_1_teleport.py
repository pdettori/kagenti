"""
T7.1 Teleport Tests

Validates session teleporting — packaging local context into a sandbox,
executing prompts with context, and cleanup.

Capability: teleport_package, teleport_deploy, teleport_prompt, teleport_cleanup
Convention: test_teleport__{description}
"""

import os
import subprocess

import pytest

from kagenti.tests.e2e.openshell.conftest import (
    kubectl_run,
    sandbox_crd_installed,
)

pytestmark = [pytest.mark.openshell, pytest.mark.teleport]

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


class TestTeleportLifecycle:
    """Full teleport lifecycle: package → deploy → prompt → cleanup."""

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
    def test_teleport__deploy_creates_sandbox(self):
        """Deploy creates a running sandbox pod with mounted context."""
        result = _run_teleport("--package")
        assert result.returncode == 0
        session_id = result.stdout.strip().split("\n")[-1]

        try:
            deploy = _run_teleport("--deploy", "--session", session_id, timeout=240)
            assert deploy.returncode == 0, f"Deploy failed: {deploy.stderr}"

            sb_name = f"teleport-{session_id}"
            check = kubectl_run(
                "get",
                "sandbox",
                sb_name,
                "-n",
                TELEPORT_NS,
                "-o",
                "jsonpath={.metadata.name}",
            )
            assert check.returncode == 0, f"Sandbox {sb_name} not found"
        finally:
            _run_teleport("--cleanup", "--session", session_id)

    @skip_no_crd
    def test_teleport__context_unpacked_in_pod(self):
        """Context is unpacked into /workspace/ inside the sandbox pod."""
        result = _run_teleport("--package")
        assert result.returncode == 0
        session_id = result.stdout.strip().split("\n")[-1]

        try:
            deploy = _run_teleport("--deploy", "--session", session_id, timeout=240)
            assert deploy.returncode == 0, f"Deploy failed: {deploy.stderr}"

            pod = kubectl_run(
                "get",
                "pods",
                "-n",
                TELEPORT_NS,
                "-l",
                f"kagenti.io/teleport-session={session_id}",
                "-o",
                "jsonpath={.items[0].metadata.name}",
            )
            assert pod.returncode == 0 and pod.stdout.strip()

            check_claude_md = kubectl_run(
                "exec",
                pod.stdout.strip(),
                "-n",
                TELEPORT_NS,
                "-c",
                "sandbox",
                "--",
                "cat",
                "/workspace/CLAUDE.md",
                timeout=15,
            )
            assert check_claude_md.returncode == 0, "CLAUDE.md not found in sandbox"
            assert "Kagenti" in check_claude_md.stdout, (
                f"CLAUDE.md doesn't contain 'Kagenti': {check_claude_md.stdout[:200]}"
            )
        finally:
            _run_teleport("--cleanup", "--session", session_id)

    @skip_no_crd
    @skip_no_llm
    def test_teleport__prompt_with_context(self):
        """Claude Code in sandbox can read teleported CLAUDE.md."""
        result = _run_teleport("--package")
        assert result.returncode == 0
        session_id = result.stdout.strip().split("\n")[-1]

        try:
            deploy = _run_teleport("--deploy", "--session", session_id, timeout=240)
            assert deploy.returncode == 0, f"Deploy failed: {deploy.stderr}"

            prompt = _run_teleport(
                "--prompt",
                "--session",
                session_id,
                "What is the name of the project described in CLAUDE.md? "
                "Reply with just the project name, nothing else.",
                timeout=180,
            )
            if prompt.returncode != 0:
                pytest.skip(
                    f"Prompt failed (LLM may be unavailable): {prompt.stderr[:200]}"
                )

            output = prompt.stdout.strip()
            assert len(output) > 0, "Empty response from teleported session"
            assert any(
                term in output.lower() for term in ["kagenti", "agent", "platform"]
            ), f"Response doesn't reference the project: {output[:200]}"
        finally:
            _run_teleport("--cleanup", "--session", session_id)

    @skip_no_crd
    def test_teleport__cleanup_removes_resources(self):
        """Cleanup deletes both Sandbox CR and ConfigMap."""
        result = _run_teleport("--package")
        assert result.returncode == 0
        session_id = result.stdout.strip().split("\n")[-1]

        _run_teleport("--deploy", "--session", session_id, timeout=240)
        _run_teleport("--cleanup", "--session", session_id)

        cm = kubectl_run(
            "get", "configmap", f"teleport-ctx-{session_id}", "-n", TELEPORT_NS
        )
        assert cm.returncode != 0, "ConfigMap should be deleted after cleanup"

        sb = kubectl_run("get", "sandbox", f"teleport-{session_id}", "-n", TELEPORT_NS)
        assert sb.returncode != 0, "Sandbox should be deleted after cleanup"

    def test_teleport__script_exists(self):
        """Teleport script exists and is executable."""
        script = _teleport_script()
        assert os.access(script, os.X_OK), f"{script} is not executable"
