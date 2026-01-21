#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/env-detect.sh"
source "$SCRIPT_DIR/../lib/logging.sh"
source "$SCRIPT_DIR/../lib/k8s-utils.sh"

log_step "74" "Deploying weather-service agent via Shipwright"

# Step 1: Apply the Shipwright Build
log_info "Creating Shipwright Build..."
kubectl apply -f "$REPO_ROOT/kagenti/examples/agents/weather_agent_shipwright_build.yaml"

# Wait for Build to be registered
run_with_timeout 30 'kubectl get build weather-service -n team1 &> /dev/null' || {
    log_error "Shipwright Build not created"
    exit 1
}
log_info "Shipwright Build created"

# Step 2: Create BuildRun to trigger the build
log_info "Triggering BuildRun..."
BUILDRUN_NAME=$(kubectl create -f "$REPO_ROOT/kagenti/examples/agents/weather_agent_shipwright_buildrun.yaml" -o jsonpath='{.metadata.name}')
log_info "BuildRun created: $BUILDRUN_NAME"

# Step 3: Wait for BuildRun to complete
log_info "Waiting for BuildRun to complete (this may take a few minutes)..."
run_with_timeout 600 "kubectl wait --for=condition=Succeeded --timeout=600s buildrun/$BUILDRUN_NAME -n team1" || {
    log_error "BuildRun did not succeed"

    # Get BuildRun status for debugging
    log_info "BuildRun status:"
    kubectl get buildrun "$BUILDRUN_NAME" -n team1 -o yaml

    # Get build pod logs
    log_info "Build pod logs:"
    BUILD_POD=$(kubectl get pods -n team1 -l build.shipwright.io/name=weather-service --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}' 2>/dev/null || echo "")
    if [ -n "$BUILD_POD" ]; then
        kubectl logs -n team1 "$BUILD_POD" --all-containers=true || true
    fi

    exit 1
}

log_success "BuildRun completed successfully"

# Step 4: Apply the Agent (uses direct image reference)
log_info "Creating Agent..."
kubectl apply -f "$REPO_ROOT/kagenti/examples/agents/weather_agent_shipwright.yaml"

# Wait for deployment
run_with_timeout 300 'until kubectl get deployment weather-service -n team1 &> /dev/null; do sleep 2; done' || {
    log_error "Deployment not created"
    kubectl logs -n kagenti-system deployment/kagenti-controller-manager --tail=100
    kubectl get agents -n team1
    kubectl describe agent weather-service -n team1
    exit 1
}

kubectl wait --for=condition=available --timeout=300s deployment/weather-service -n team1 || {
    log_error "Deployment not available"
    kubectl get events -n team1 --sort-by='.lastTimestamp'
    exit 1
}

log_success "Weather-service deployed via Shipwright"
