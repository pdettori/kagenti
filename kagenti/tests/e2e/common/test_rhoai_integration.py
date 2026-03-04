#!/usr/bin/env python3
"""
RHOAI Integration E2E Tests

Tests RHOAI deployment health and mesh trust when RHOAI is enabled.

Usage:
    pytest tests/e2e/common/test_rhoai_integration.py -v
"""

import subprocess

import pytest
from kubernetes import client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException


@pytest.fixture(scope="session")
def k8s_custom_client():
    """
    Load Kubernetes configuration and return CustomObjectsApi client.

    Returns:
        kubernetes.client.CustomObjectsApi: Kubernetes custom objects API client

    Raises:
        pytest.skip: If cannot connect to Kubernetes cluster
    """
    try:
        k8s_config.load_kube_config()
    except k8s_config.ConfigException:
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException as e:
            pytest.skip(f"Could not load Kubernetes config: {e}")

    return client.CustomObjectsApi()


class TestRHOAIOperatorHealth:
    """Test RHOAI operator deployment health."""

    @pytest.mark.requires_features(["rhoai"])
    def test_rhoai_operator_namespace_exists(self, k8s_client):
        """Verify redhat-ods-operator namespace exists."""
        try:
            ns = k8s_client.read_namespace(name="redhat-ods-operator")
            assert ns is not None
        except ApiException as e:
            pytest.fail(f"redhat-ods-operator namespace not found: {e}")

    @pytest.mark.requires_features(["rhoai"])
    def test_rhoai_operator_running(self, k8s_client):
        """Verify RHOAI operator pod is Running."""
        pods = k8s_client.list_namespaced_pod(
            namespace="redhat-ods-operator",
            label_selector="name=rhods-operator",
        )
        assert len(pods.items) > 0, "No RHOAI operator pods found"
        for pod in pods.items:
            assert pod.status.phase == "Running", (
                f"RHOAI operator pod {pod.metadata.name} is {pod.status.phase}"
            )


class TestRHOAIDataScienceCluster:
    """Test DataScienceCluster CR health."""

    @pytest.mark.requires_features(["rhoai"])
    def test_datasciencecluster_exists(self, k8s_custom_client):
        """Verify DataScienceCluster CR exists."""
        dsc = k8s_custom_client.get_cluster_custom_object(
            group="datasciencecluster.opendatahub.io",
            version="v1",
            plural="datascienceclusters",
            name="default-dsc",
        )
        assert dsc is not None

    @pytest.mark.requires_features(["rhoai"])
    def test_datasciencecluster_ready(self, k8s_custom_client):
        """Verify DataScienceCluster is in Ready phase."""
        dsc = k8s_custom_client.get_cluster_custom_object(
            group="datasciencecluster.opendatahub.io",
            version="v1",
            plural="datascienceclusters",
            name="default-dsc",
        )
        phase = dsc.get("status", {}).get("phase", "Unknown")
        assert phase == "Ready", f"DataScienceCluster phase is {phase}, expected Ready"

    @pytest.mark.requires_features(["rhoai"])
    def test_kserve_controller_running(self, k8s_client):
        """Verify KServe controller manager is Running."""
        pods = k8s_client.list_namespaced_pod(
            namespace="redhat-ods-applications",
            label_selector="control-plane=kserve-controller-manager",
        )
        assert len(pods.items) > 0, "No KServe controller pods found"
        for pod in pods.items:
            assert pod.status.phase == "Running", (
                f"KServe controller pod {pod.metadata.name} is {pod.status.phase}"
            )


class TestRHOAIMeshTrust:
    """Test mesh trust when both Istio control planes exist."""

    @pytest.mark.requires_features(["rhoai", "istio"])
    def test_ztunnel_no_bad_signature(self, k8s_client):
        """Verify ztunnel logs show no BadSignature errors."""
        result = subprocess.run(
            [
                "kubectl",
                "logs",
                "-n",
                "istio-ztunnel",
                "-l",
                "app=ztunnel",
                "--tail=200",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert "BadSignature" not in result.stdout, (
            "ztunnel logs contain BadSignature errors - CA mismatch detected"
        )

    @pytest.mark.requires_features(["rhoai"])
    def test_rhoai_dashboard_accessible(self, k8s_custom_client):
        """Verify RHOAI Dashboard is accessible via route or gateway."""
        # RHOAI 3.x uses data-science-gateway in openshift-ingress
        # RHOAI 2.x used rhods-dashboard route in redhat-ods-applications
        found = False
        for ns, name in [
            ("openshift-ingress", "data-science-gateway"),
            ("redhat-ods-applications", "rhods-dashboard"),
        ]:
            try:
                route = k8s_custom_client.get_namespaced_custom_object(
                    group="route.openshift.io",
                    version="v1",
                    namespace=ns,
                    plural="routes",
                    name=name,
                )
                host = route.get("spec", {}).get("host", "")
                if host:
                    found = True
                    break
            except Exception:
                continue
        assert found, (
            "No RHOAI Dashboard route found (checked data-science-gateway "
            "in openshift-ingress and rhods-dashboard in redhat-ods-applications)"
        )
