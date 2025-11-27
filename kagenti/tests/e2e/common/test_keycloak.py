#!/usr/bin/env python3
"""
Keycloak E2E Tests - Common to Both Operators

Tests Keycloak deployment health and authentication (when enabled).

Usage:
    pytest tests/e2e/common/test_keycloak.py -v

Environment Variables:
    KEYCLOAK_ADMIN_USER: Admin username (default: admin)
    KEYCLOAK_ADMIN_PASSWORD: Admin password (default: admin)
    KEYCLOAK_URL: Keycloak URL (default: http://localhost:8081 - port-forwarded)
"""

import os
import pytest
import httpx
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
        deployment_error = None
        statefulset_error = None

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
        except ApiException as e:
            deployment_error = str(e)

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
            return  # Success
        except ApiException as e:
            statefulset_error = str(e)

        # Both failed - report both errors
        pytest.fail(
            f"Keycloak not found as deployment or statefulset.\n"
            f"Deployment error: {deployment_error}\n"
            f"StatefulSet error: {statefulset_error}"
        )

    @pytest.mark.requires_features(["keycloak"])
    @pytest.mark.asyncio
    async def test_keycloak_admin_login(self):
        """
        Test Keycloak admin authentication.

        Verifies that we can authenticate with the Keycloak admin user
        and obtain an access token.

        Note: This test requires network access to Keycloak via port-forward.
        Set KEYCLOAK_URL to override the default (http://localhost:8081).
        If Keycloak is not accessible, the test will skip gracefully.
        """
        # Get credentials from environment
        admin_user = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
        admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
        # Use localhost:8081 for port-forwarded access (set up by test infrastructure)
        keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8081")

        # Construct token endpoint
        token_url = f"{keycloak_url}/realms/master/protocol/openid-connect/token"

        # Prepare auth request
        auth_data = {
            "client_id": "admin-cli",
            "username": admin_user,
            "password": admin_password,
            "grant_type": "password",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    token_url,
                    data=auth_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                # Check if authentication was successful
                assert response.status_code == 200, (
                    f"Keycloak admin login failed with status {response.status_code}. "
                    f"Response: {response.text}"
                )

                # Verify we got an access token
                token_data = response.json()
                assert (
                    "access_token" in token_data
                ), f"No access_token in response. Response: {token_data}"
                assert len(token_data["access_token"]) > 0, "Access token is empty"

                print(f"\n✓ Successfully authenticated to Keycloak as {admin_user}")
                print(f"  Token type: {token_data.get('token_type', 'unknown')}")
                print(
                    f"  Expires in: {token_data.get('expires_in', 'unknown')} seconds"
                )

            except httpx.ConnectError as e:
                # Connection errors are expected when Keycloak is not port-forwarded
                # or not accessible (e.g., in CI without port-forward setup)
                error_msg = str(e).lower()
                if any(
                    keyword in error_msg
                    for keyword in [
                        "name resolution",
                        "connection refused",
                        "failed to establish",
                    ]
                ):
                    pytest.skip(
                        f"Keycloak not accessible at {keycloak_url}. "
                        "This test requires port-forwarding to Keycloak service. "
                        "Set up port-forward with: kubectl port-forward -n keycloak svc/keycloak 8081:8080"
                    )
                else:
                    pytest.fail(f"Network error connecting to Keycloak: {e}")
            except httpx.RequestError as e:
                pytest.fail(
                    f"Network error connecting to Keycloak at {keycloak_url}: {e}"
                )
            except Exception as e:
                pytest.fail(f"Unexpected error during Keycloak authentication: {e}")


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
