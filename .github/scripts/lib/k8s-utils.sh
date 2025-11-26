#!/usr/bin/env bash
# Kubernetes Utilities Library
# Provides helper functions for Kubernetes operations

# Wait for deployment to be available
wait_for_deployment() {
    local deployment="$1"
    local namespace="$2"
    local timeout="${3:-300}"

    kubectl wait --for=condition=available --timeout="${timeout}s" "deployment/$deployment" -n "$namespace" || {
        echo "ERROR: Deployment $deployment not ready in $namespace"
        kubectl describe "deployment/$deployment" -n "$namespace"
        kubectl get events -n "$namespace" --sort-by='.lastTimestamp' | tail -30
        return 1
    }
}

# Wait for pod to be ready
wait_for_pod() {
    local selector="$1"
    local namespace="$2"
    local timeout="${3:-300}"

    kubectl wait --for=condition=ready --timeout="${timeout}s" pod -l "$selector" -n "$namespace" || {
        echo "ERROR: Pod with selector $selector not ready in $namespace"
        kubectl get pods -l "$selector" -n "$namespace"
        kubectl logs -n "$namespace" -l "$selector" --tail=50 || true
        return 1
    }
}

# Wait for CRD to be established
wait_for_crd() {
    local crd="$1"
    local timeout="${2:-300}"

    kubectl wait --for condition=established --timeout="${timeout}s" "crd/$crd" || {
        echo "ERROR: CRD $crd not established"
        kubectl get crds | grep -E 'kagenti|mcp|toolhive' || echo "No related CRDs found"
        return 1
    }
}

# Check if pod is ready
check_pod_ready() {
    local selector="$1"
    local namespace="$2"

    kubectl get pods -l "$selector" -n "$namespace" -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' | grep -q "True"
}

# Get pod logs with selector
get_pod_logs() {
    local selector="$1"
    local namespace="$2"
    local tail="${3:-50}"

    kubectl logs -n "$namespace" -l "$selector" --tail="$tail" --all-containers=true || true
}

# Start port-forward in background
port_forward_background() {
    local resource="$1"
    local namespace="$2"
    local local_port="$3"
    local remote_port="$4"
    local log_file="${5:-/tmp/port-forward.log}"

    kubectl port-forward -n "$namespace" "$resource" "${local_port}:${remote_port}" > "$log_file" 2>&1 &
    echo $!
}
