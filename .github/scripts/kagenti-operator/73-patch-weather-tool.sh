#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/env-detect.sh"
source "$SCRIPT_DIR/../lib/logging.sh"

log_step "73" "Patching weather-tool for writable /tmp"

# Wait for StatefulSet
timeout 60 bash -c 'until kubectl get statefulset weather-tool -n team1 &> /dev/null; do sleep 2; done' || {
    log_error "StatefulSet not created"
    kubectl get statefulset -n team1
    exit 1
}

# Patch StatefulSet
kubectl patch statefulset weather-tool -n team1 -p '{"spec":{"template":{"spec":{"volumes":[{"name":"tmp","emptyDir":{}}],"containers":[{"name":"mcp","volumeMounts":[{"name":"tmp","mountPath":"/tmp"}]}]}}}}'

# Delete pod to force recreation
kubectl delete pod -n team1 -l app=weather-tool --wait=false || true

# Wait for new pod
kubectl wait --for=condition=ready --timeout=300s pod -n team1 -l app=weather-tool || {
    log_error "Pod not ready after patch"
    kubectl get pods -n team1 -l app=weather-tool
    kubectl logs -n team1 -l app=weather-tool --tail=50 || true
    exit 1
}

log_success "Weather-tool patched"
