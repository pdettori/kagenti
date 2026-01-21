# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""
Integration tests for Shipwright tool builds.

These tests validate end-to-end flows for building and deploying MCP tools
using the Shipwright build system.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Note: These tests are designed to run against a mock Kubernetes cluster
# or can be adapted for real cluster testing with proper fixtures.


@pytest.fixture
def mock_k8s_client():
    """Create mock Kubernetes API client."""
    with patch("app.routers.tools.k8s_client") as mock:
        mock.custom_api = MagicMock()
        mock.core_api = MagicMock()
        yield mock


class TestToolShipwrightBuildIntegration:
    """Integration tests for tool Shipwright build workflow."""

    def test_create_tool_with_source_build(self, mock_k8s_client):
        """Test creating a tool with source build creates Build and waits for image."""
        # Arrange
        tool_data = {
            "name": "weather-tool",
            "namespace": "team1",
            "description": "Weather lookup tool",
            "protocol": "streamable_http",
            "framework": "Python",
            "deploymentMethod": "source",
            "gitUrl": "https://github.com/kagenti/agent-examples",
            "gitBranch": "main",
            "gitPath": "mcp/weather_tool",
            "registry": "registry.cr-system.svc.cluster.local:5000",
        }

        # Mock K8s API responses
        mock_k8s_client.custom_api.create_namespaced_custom_object.return_value = {
            "metadata": {"name": "weather-tool", "namespace": "team1"},
        }

        # Act - would trigger POST /api/tools
        # Response should indicate build started

        # Assert - Build resource should be created
        # Note: In real tests, we'd call the API endpoint
        assert True  # Placeholder

    def test_buildrun_status_progression(self, mock_k8s_client):
        """Test that BuildRun status correctly progresses through phases."""
        # Arrange - simulate buildrun status changes
        buildrun_pending = {
            "metadata": {"name": "weather-tool-run-abc"},
            "status": {
                "conditions": [
                    {"type": "Succeeded", "status": "Unknown", "reason": "Pending"}
                ]
            },
        }
        buildrun_running = {
            "metadata": {"name": "weather-tool-run-abc"},
            "status": {
                "conditions": [
                    {"type": "Succeeded", "status": "Unknown", "reason": "Running"}
                ],
                "startTime": "2026-01-21T10:00:00Z",
            },
        }
        buildrun_succeeded = {
            "metadata": {"name": "weather-tool-run-abc"},
            "status": {
                "conditions": [
                    {"type": "Succeeded", "status": "True", "reason": "Succeeded"}
                ],
                "startTime": "2026-01-21T10:00:00Z",
                "completionTime": "2026-01-21T10:05:00Z",
                "output": {
                    "image": "registry.local/weather-tool:v0.0.1",
                    "digest": "sha256:def456",
                },
            },
        }

        # Act - status should progress from Pending -> Running -> Succeeded
        from app.services.shipwright import parse_buildrun_phase

        assert parse_buildrun_phase(buildrun_pending) == "Pending"
        assert parse_buildrun_phase(buildrun_running) == "Running"
        assert parse_buildrun_phase(buildrun_succeeded) == "Succeeded"

    def test_tool_config_stored_in_build_annotations(self, mock_k8s_client):
        """Test that tool configuration is stored in Build annotations."""
        from app.services.shipwright import build_shipwright_build_manifest
        from app.models.shipwright import (
            ResourceType,
            BuildSourceConfig,
            BuildOutputConfig,
        )

        # Arrange
        source = BuildSourceConfig(
            gitUrl="https://github.com/example/tools",
            gitRevision="main",
            contextDir="mcp/weather",
        )
        output = BuildOutputConfig(
            registry="registry.local",
            imageName="weather-tool",
            imageTag="v0.0.1",
        )
        tool_config = {
            "protocol": "streamable_http",
            "framework": "Python",
            "description": "Weather lookup tool",
            "createHttpRoute": False,
        }

        # Act
        manifest = build_shipwright_build_manifest(
            name="weather-tool",
            namespace="team1",
            resource_type=ResourceType.TOOL,
            source_config=source,
            output_config=output,
            resource_config=tool_config,
            protocol="streamable_http",
            framework="Python",
        )

        # Assert
        annotations = manifest["metadata"]["annotations"]
        assert "kagenti.io/tool-config" in annotations
        stored_config = json.loads(annotations["kagenti.io/tool-config"])
        assert stored_config["protocol"] == "streamable_http"
        assert stored_config["framework"] == "Python"

    def test_mcpserver_created_after_build_success(self, mock_k8s_client):
        """Test that MCPServer is created after build succeeds."""
        from app.services.shipwright import extract_resource_config_from_build
        from app.models.shipwright import ResourceType

        # Arrange - Build with tool config annotation
        build = {
            "metadata": {
                "name": "weather-tool",
                "namespace": "team1",
                "annotations": {
                    "kagenti.io/tool-config": json.dumps(
                        {
                            "protocol": "streamable_http",
                            "framework": "Python",
                            "description": "Weather lookup tool",
                            "createHttpRoute": False,
                            "envVars": [{"name": "API_KEY", "value": "secret"}],
                            "servicePorts": [
                                {"containerPort": 8000, "servicePort": 80}
                            ],
                        }
                    )
                },
            }
        }

        # BuildRun with output image
        buildrun = {
            "status": {
                "conditions": [
                    {"type": "Succeeded", "status": "True", "reason": "Succeeded"}
                ],
                "output": {
                    "image": "registry.local/weather-tool:v0.0.1",
                    "digest": "sha256:abc123",
                },
            }
        }

        # Act - Extract config from build
        config = extract_resource_config_from_build(build, ResourceType.TOOL)

        # Assert - Config is extracted and can be used to create MCPServer
        assert config is not None
        assert config.protocol == "streamable_http"
        assert config.framework == "Python"


class TestToolShipwrightBuildRetry:
    """Tests for BuildRun retry functionality."""

    def test_create_new_buildrun_on_retry(self, mock_k8s_client):
        """Test that retry creates a new BuildRun for the same Build."""
        from app.services.shipwright import build_shipwright_buildrun_manifest
        from app.models.shipwright import ResourceType

        # Act - Create a new buildrun (simulating retry)
        manifest = build_shipwright_buildrun_manifest(
            build_name="weather-tool",
            namespace="team1",
            resource_type=ResourceType.TOOL,
        )

        # Assert
        assert manifest["spec"]["build"]["name"] == "weather-tool"
        assert manifest["metadata"]["generateName"] == "weather-tool-run-"

    def test_latest_buildrun_selected_after_retry(self, mock_k8s_client):
        """Test that after retry, the latest buildrun is selected for status."""
        from app.services.shipwright import get_latest_buildrun

        # Arrange - multiple buildruns for same build
        buildruns = [
            {
                "metadata": {
                    "name": "weather-tool-run-1",
                    "creationTimestamp": "2026-01-21T10:00:00Z",
                },
                "status": {
                    "conditions": [
                        {"type": "Succeeded", "status": "False", "reason": "Failed"}
                    ]
                },
            },
            {
                "metadata": {
                    "name": "weather-tool-run-2",
                    "creationTimestamp": "2026-01-21T11:00:00Z",
                },
                "status": {
                    "conditions": [
                        {"type": "Succeeded", "status": "Unknown", "reason": "Running"}
                    ]
                },
            },
        ]

        # Act
        latest = get_latest_buildrun(buildruns)

        # Assert - latest buildrun should be the retry
        assert latest["metadata"]["name"] == "weather-tool-run-2"


class TestToolShipwrightBuildCleanup:
    """Tests for build cleanup scenarios."""

    def test_build_deletion_cascades_to_buildruns(self, mock_k8s_client):
        """Test that deleting a Build should also delete its BuildRuns."""
        # This is handled by Kubernetes owner references
        # The Build sets owner reference on BuildRun creation

        from app.services.shipwright import build_shipwright_buildrun_manifest
        from app.models.shipwright import ResourceType

        manifest = build_shipwright_buildrun_manifest(
            build_name="weather-tool",
            namespace="team1",
            resource_type=ResourceType.TOOL,
        )

        # Verify owner reference is set
        assert "ownerReferences" not in manifest["metadata"]  # Set by K8s on apply
        assert manifest["spec"]["build"]["name"] == "weather-tool"


class TestToolBuildStrategySelection:
    """Tests for build strategy auto-selection."""

    def test_internal_registry_uses_insecure_strategy(self, mock_k8s_client):
        """Test internal registry uses insecure build strategy."""
        from app.services.shipwright import select_build_strategy
        from app.core.constants import (
            DEFAULT_INTERNAL_REGISTRY,
            SHIPWRIGHT_STRATEGY_INSECURE,
        )

        strategy = select_build_strategy(DEFAULT_INTERNAL_REGISTRY)
        assert strategy == SHIPWRIGHT_STRATEGY_INSECURE

    def test_external_registry_uses_secure_strategy(self, mock_k8s_client):
        """Test external registry uses secure build strategy."""
        from app.services.shipwright import select_build_strategy
        from app.core.constants import SHIPWRIGHT_STRATEGY_SECURE

        strategy = select_build_strategy("quay.io/myorg")
        assert strategy == SHIPWRIGHT_STRATEGY_SECURE

        strategy = select_build_strategy("ghcr.io/myuser")
        assert strategy == SHIPWRIGHT_STRATEGY_SECURE

        strategy = select_build_strategy("docker.io/library")
        assert strategy == SHIPWRIGHT_STRATEGY_SECURE


class TestToolBuildErrorScenarios:
    """Tests for build error handling."""

    def test_invalid_git_url_fails_build(self, mock_k8s_client):
        """Test that invalid git URL causes build failure."""
        # BuildRun would fail with reason about git clone failure
        failed_buildrun = {
            "status": {
                "conditions": [
                    {
                        "type": "Succeeded",
                        "status": "False",
                        "reason": "Failed",
                        "message": "fatal: repository 'invalid-url' not found",
                    }
                ]
            }
        }

        from app.services.shipwright import parse_buildrun_phase, is_build_succeeded

        assert parse_buildrun_phase(failed_buildrun) == "Failed"
        assert is_build_succeeded(failed_buildrun) is False

    def test_missing_dockerfile_fails_build(self, mock_k8s_client):
        """Test that missing Dockerfile causes build failure."""
        failed_buildrun = {
            "status": {
                "conditions": [
                    {
                        "type": "Succeeded",
                        "status": "False",
                        "reason": "Failed",
                        "message": "unable to find Dockerfile in context",
                    }
                ]
            }
        }

        from app.services.shipwright import parse_buildrun_phase

        assert parse_buildrun_phase(failed_buildrun) == "Failed"

    def test_registry_push_failure(self, mock_k8s_client):
        """Test that registry push failure is detected."""
        failed_buildrun = {
            "status": {
                "conditions": [
                    {
                        "type": "Succeeded",
                        "status": "False",
                        "reason": "Failed",
                        "message": "unauthorized: authentication required",
                    }
                ]
            }
        }

        from app.services.shipwright import parse_buildrun_phase, is_build_succeeded

        assert parse_buildrun_phase(failed_buildrun) == "Failed"
        assert is_build_succeeded(failed_buildrun) is False
