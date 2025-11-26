#!/usr/bin/env python3
"""
Keycloak E2E Tests - Common to Both Operators

Tests Keycloak deployment health (when enabled).

Usage:
    pytest tests/e2e/common/test_keycloak.py -v
"""

import pytest
from kubernetes.client.rest import ApiException


class TestKeycloakDeployment:
    """Test Keycloak deployment health."""

    @pytest.mark.requires_features(["keycloak"])
    def test_keycloak_namespace_exists(self, k8s_client):
        """Verify keycloak namespace exists."""
        try:
            namespace = k8s_client.read_namespace(name="keycloak")
            assert namespace is not None, "keycloak namespace not found"
        except ApiException as e:
            pytest.fail(f"keycloak namespace not found: {e}")

    @pytest.mark.critical
    @pytest.mark.requires_features(["keycloak"])
    def test_keycloak_deployment_ready(self, k8s_apps_client):
        """Verify Keycloak deployment or statefulset is ready."""
        # Try deployment first
        try:
            deployment = k8s_apps_client.read_namespaced_deployment(
                name="keycloak", namespace="keycloak"
            )

            desired_replicas = deployment.spec.replicas or 1
            ready_replicas = deployment.status.ready_replicas or 0

            assert (
                ready_replicas >= desired_replicas
            ), f"Keycloak deployment not ready: {ready_replicas}/{desired_replicas} replicas"
            return  # Success
        except ApiException:
            pass  # Try statefulset

        # Try statefulset
        try:
            statefulset = k8s_apps_client.read_namespaced_stateful_set(
                name="keycloak", namespace="keycloak"
            )

            desired_replicas = statefulset.spec.replicas or 1
            ready_replicas = statefulset.status.ready_replicas or 0

            assert (
                ready_replicas >= desired_replicas
            ), f"Keycloak statefulset not ready: {ready_replicas}/{desired_replicas} replicas"
        except ApiException as e:
            pytest.fail(f"Keycloak deployment/statefulset not found: {e}")


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
