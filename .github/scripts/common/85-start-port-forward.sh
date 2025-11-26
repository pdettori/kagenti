#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/env-detect.sh"
source "$SCRIPT_DIR/../lib/logging.sh"

log_step "85" "Starting port-forward"

# Get pod name
POD_NAME=$(kubectl get pod -n team1 -l app.kubernetes.io/name=weather-service -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    log_error "No weather-service pod found"
    kubectl get pods -n team1
    exit 1
fi

log_info "Port-forwarding to pod: $POD_NAME"

# Start port-forward in background
kubectl port-forward -n team1 pod/$POD_NAME 8000:8000 > /tmp/port-forward.log 2>&1 &
PORT_FORWARD_PID=$!

if [ "$IS_CI" = true ]; then
    echo "PORT_FORWARD_PID=$PORT_FORWARD_PID" >> $GITHUB_ENV
else
    echo $PORT_FORWARD_PID > /tmp/port-forward.pid
fi

# Wait for port-forward to be ready
for i in {1..10}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1 || curl -s http://localhost:8000/ >/dev/null 2>&1; then
        log_success "Port-forward is ready"
        exit 0
    fi
    sleep 1
done

log_warn "Port-forward may not be ready"
