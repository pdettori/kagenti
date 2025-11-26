#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/env-detect.sh"
source "$SCRIPT_DIR/../lib/logging.sh"

log_step "72" "Deploying weather-tool via Toolhive"

kubectl apply -f "$REPO_ROOT/kagenti/examples/mcpservers/weather_tool.yaml"

# Wait for deployment
timeout 300 bash -c 'until kubectl get deployment weather-tool -n team1 &> /dev/null; do sleep 2; done' || {
    log_error "Deployment not created after 300s"
    kubectl get mcpservers -n team1
    kubectl describe mcpserver weather-tool -n team1
    kubectl logs -n toolhive-system deployment/toolhive-operator --tail=100 || true
    exit 1
}

kubectl wait --for=condition=available --timeout=300s deployment/weather-tool -n team1 || {
    log_error "Deployment not available"
    kubectl get events -n team1 --sort-by='.lastTimestamp'
    kubectl describe deployment weather-tool -n team1
    exit 1
}

log_success "Weather-tool deployed"
