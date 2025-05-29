#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

set -x # echo so that users can understand what is happening
set -e # exit on error

# Function to check if an env variable is set
check_env_var() {
    local var_name="$1"
    if [ -z "${!var_name}" ]; then
        echo -e "\033[0;31mError:\033[0m The environment variable \033[1;33m${var_name}\033[0m is not set."
        return 1
    else
        echo -e "\033[0;32mSuccess:\033[0m The environment variable \033[1;33m${var_name}\033[0m is set."
        return 0
    fi
}

# function to preload a list of images in kind
preload_images_in_kind() {
  local KIND_CLUSTER_NAME="agent-platform"  
  local images=("$@")             
  for image in "${images[@]}"; do
    echo "Pulling image: $image"
    docker pull "$image"
    echo "Loading image into kind cluster: $image"
    kind load docker-image "$image" --name "$KIND_CLUSTER_NAME"
  done
  echo "All specified images have been preloaded into kind."
}

# Function to check if the deployment exists
deployment_exists() {
  local NAMESPACE=$1
  local DEPLOYMENT_NAME=$2  
  kubectl get deployment -n "$NAMESPACE" "$DEPLOYMENT_NAME" &> /dev/null
}

:
: -------------------------------------------------------------------------
: "Load env variables"
: 
if [ -f ${SCRIPT_DIR}/.env ]; then
    source ${SCRIPT_DIR}/.env
else
    echo -e "\033[0;31mError:\033[0m .env file not found."
    exit 1
fi

:
: -------------------------------------------------------------------------
: "Checking env variables are all set"
: 
env_vars=("TOKEN" "REPO_USER" "OPENAI_API_KEY")
unset_flag=0

# Loop through each env variable and check
for var in "${env_vars[@]}"; do
    check_env_var "$var" || unset_flag=1
done

# Exit the script if at least one variable is not set
if [ $unset_flag -eq 1 ]; then
    echo -e "\033[0;31mExiting:\033[0m One or more required environment variables are not set."
    exit 1
fi

echo -e "\033[0;32mAll env vars checks passed.\033[0m"

:
: -------------------------------------------------------------------------
: "Create a new kind cluster with kagenti operator"
: 
curl -sSL https://raw.githubusercontent.com/kagenti/kagenti-operator/main/beeai/scripts/install.sh | bash


:
: -------------------------------------------------------------------------
: "Preload images to avoid dockerhub pull rate limiting"
: 
preload_images_in_kind \
    "prom/prometheus:v3.1.0" \
    "kubernetesui/dashboard-api:1.13.0" \
    "kubernetesui/dashboard-auth:1.3.0" \
    "kong:3.8" \
    "kubernetesui/dashboard-metrics-scraper:1.2.2" \
    "kubernetesui/dashboard-web:1.7.0"
    

:
: -------------------------------------------------------------------------
: "Install Istio Ambient using helm"
: 
:
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update
helm install istio-base istio/base -n istio-system --create-namespace --wait
kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null || \
  kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.3.0-rc.1/standard-install.yaml
helm install istiod istio/istiod --namespace istio-system --set profile=ambient --wait
helm install istio-cni istio/cni -n istio-system --set profile=ambient --wait
helm install ztunnel istio/ztunnel -n istio-system --wait

:
: -------------------------------------------------------------------------
: "Check all istio pods running"
: 
:
kubectl rollout status -n istio-system daemonset/ztunnel 
kubectl rollout status -n istio-system daemonset/istio-cni-node 
kubectl rollout status -n istio-system deployment/istiod 

:
: -------------------------------------------------------------------------
: "Install Prometheus and Kiali"
: 
:
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.25/samples/addons/prometheus.yaml
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.25/samples/addons/kiali.yaml

: -------------------------------------------------------------------------
: "Check all kiali and prometheus pods running"
: 
:
kubectl rollout status -n istio-system deployment/kiali
kubectl rollout status -n istio-system deployment/prometheus

:
: -------------------------------------------------------------------------
: "Create gateway and add nodeport service for external access"
: 
:
kubectl apply -f ${SCRIPT_DIR}/resources/http-gateway.yaml
kubectl apply -f ${SCRIPT_DIR}/resources/gateway-nodeport.yaml
kubectl annotate gateway http networking.istio.io/service-type=ClusterIP --namespace=kagenti-system

:
: -------------------------------------------------------------------------
: "Add waypoint gateway for egress to default namespace"
: 
:
kubectl apply -f ${SCRIPT_DIR}/resources/gateway-waypoint.yaml
kubectl rollout status -n default deployment/waypoint

:
: -------------------------------------------------------------------------
: "Add http routing for kiali"
: 
:
kubectl apply -f ${SCRIPT_DIR}/resources/kiali-route.yaml
kubectl label ns istio-system shared-gateway-access="true"


:
: -------------------------------------------------------------------------
: "Install Keycloak"
: 
:
kubectl apply -f ${SCRIPT_DIR}/../identity/keycloak_token_exchange/resources/keycloak/namespace.yaml
kubectl apply -n keycloak -f https://raw.githubusercontent.com/keycloak/keycloak-quickstarts/refs/heads/main/kubernetes/keycloak.yaml
kubectl scale -n keycloak statefulsets keycloak --replicas 1
kubectl patch statefulset keycloak -n keycloak --patch '
spec:
  template:
    spec:
      containers:
      - name: keycloak
        env:
        - name: KC_PROXY_HEADERS
          value: forwarded
'

:
: -------------------------------------------------------------------------
: "Check it is started"
: 
:
kubectl rollout status -n keycloak statefulset/keycloak

:
: -------------------------------------------------------------------------
: "Add http routing for keycloak"
: "Console access should be at http://keycloak.localtest.me:8080/admin/master/console/"
: 
:
kubectl apply -f ${SCRIPT_DIR}/resources/keycloak-route.yaml
kubectl label ns keycloak shared-gateway-access="true"
kubectl label namespace keycloak istio.io/dataplane-mode=ambient


:
: -------------------------------------------------------------------------
: "Create github credentials secret"
: 
:
if ! kubectl get secret github-token-secret >/dev/null 2>&1; then
    kubectl create secret generic github-token-secret --from-literal=token="${TOKEN}"
else
    echo "secret github-token-secret already exists"  
fi

:
: -------------------------------------------------------------------------
: "Create openai credentials secret"
: 
:
if ! kubectl get secret openai-secret >/dev/null 2>&1; then
    kubectl create secret generic openai-secret --from-literal=apikey="${OPENAI_API_KEY}"
else
    echo "secret openai-secret already exists"  
fi

:
: -------------------------------------------------------------------------
: "Build and deploy the a2a langgraph currency agent"
: 
:
sed  "s|\${REPO_USER}|${REPO_USER}|g" ${SCRIPT_DIR}/../../examples/templates/a2a/a2a-currency-agent.yaml | kubectl apply -f -
until deployment_exists default a2a-currency-agent; do
  sleep 2
done
kubectl rollout status -n default deployment/a2a-currency-agent

:
: -------------------------------------------------------------------------
: "Build and deploy the a2a contact extractor agent"
: 
:
sed  "s|\${REPO_USER}|${REPO_USER}|g" ${SCRIPT_DIR}/../../examples/templates/a2a/a2a-contact-extractor-agent.yaml | kubectl apply -f -
until deployment_exists default a2a-contact-extractor-agent; do
  sleep 2
done
kubectl rollout status -n default deployment/a2a-contact-extractor-agent

:
: -------------------------------------------------------------------------
: "Build and deploy the acp ollama researcher agent"
: 
:
sed  "s|\${REPO_USER}|${REPO_USER}|g" ${SCRIPT_DIR}/../../examples/templates/acp/acp-ollama-researcher.yaml | kubectl apply -f -
until deployment_exists default acp-ollama-researcher; do
  sleep 2
done
kubectl rollout status -n default deployment/acp-ollama-researcher

:
: -------------------------------------------------------------------------
: "Build and deploy the mcp web fetch tool"
: 
:
sed  "s|\${REPO_USER}|${REPO_USER}|g" ${SCRIPT_DIR}/../../examples/templates/mcp/mcp-web-fetch.yaml | kubectl apply -f -
until deployment_exists default mcp-web-fetch; do
  sleep 2
done
kubectl rollout status -n default deployment/mcp-web-fetch

:
: -------------------------------------------------------------------------
: "Build and deploy the mcp get weather tool"
: 
:
sed  "s|\${REPO_USER}|${REPO_USER}|g" ${SCRIPT_DIR}/../../examples/templates/mcp/mcp-get-weather.yaml | kubectl apply -f -
until deployment_exists default mcp-get-weather; do
  sleep 2
done
kubectl rollout status -n default deployment/mcp-get-weather

:
: -------------------------------------------------------------------------
: "Build and deploy the acp ollama weather service agent"
: 
:
sed  "s|\${REPO_USER}|${REPO_USER}|g" ${SCRIPT_DIR}/../../examples/templates/acp/acp-ollama-weather-service.yaml | kubectl apply -f -
until deployment_exists default acp-weather-service; do
  sleep 2
done
kubectl rollout status -n default deployment/acp-weather-service

:
: -------------------------------------------------------------------------
: "Add http routing for all agents and tools"
: 
:
kubectl apply -f ${SCRIPT_DIR}/resources/routes

:
: -------------------------------------------------------------------------
: "Add service routes for egress"
: 
:
kubectl apply -f ${SCRIPT_DIR}/resources/service-entries


:
: -------------------------------------------------------------------------
: "Label default namespace for shared gateway access and waypoint egress"
: 
:
kubectl label ns default shared-gateway-access="true"
kubectl label ns default istio.io/use-waypoint=waypoint

:
: -------------------------------------------------------------------------
: "Add agents to the ambient mesh"
: 
:
kubectl label namespace default istio.io/dataplane-mode=ambient

:
: -------------------------------------------------------------------------
: "Install arize phonenix observability dashboard and enable gateway access to UI"
: 
:
kubectl apply -n kagenti-system -f ${SCRIPT_DIR}/resources/phoenix.yaml
kubectl apply -n kagenti-system -f ${SCRIPT_DIR}/resources/phoenix-route.yaml
kubectl label ns kagenti-system shared-gateway-access="true"

:
: -------------------------------------------------------------------------
: "Ensure phoenix and db started"
: 
:
kubectl rollout status -n kagenti-system statefulset/postgres
kubectl rollout status -n kagenti-system statefulset/phoenix

:
: -------------------------------------------------------------------------
: "Install otel collector configured to upload to phoenix"
: 
:
kubectl apply -n kagenti-system -f ${SCRIPT_DIR}/resources/otel-collector.yaml

:
: -------------------------------------------------------------------------
: "Ensure otel collector is started"
: 
:
kubectl rollout status -n kagenti-system deployment/otel-collector


:
: -------------------------------------------------------------------------
: "Label Agents and Tools"
: 
:
kubectl label agent mcp-get-weather kagenti.io/type=tool
kubectl label agent mcp-get-weather kagenti.io/protocol=MCP
kubectl label agent mcp-get-weather kagenti.io/framework=python

kubectl label agent mcp-web-fetch kagenti.io/type=tool
kubectl label agent mcp-web-fetch kagenti.io/protocol=MCP
kubectl label agent mcp-web-fetch kagenti.io/framework=python

kubectl label agent a2a-currency-agent kagenti.io/type=agent
kubectl label agent a2a-currency-agent kagenti.io/protocol=A2A
kubectl label agent a2a-currency-agent kagenti.io/framework=LangGraph

kubectl label agent a2a-contact-extractor-agent kagenti.io/type=agent
kubectl label agent a2a-contact-extractor-agent kagenti.io/protocol=A2A
kubectl label agent a2a-contact-extractor-agent kagenti.io/framework=Marvin

kubectl label agent acp-ollama-researcher kagenti.io/type=agent
kubectl label agent acp-ollama-researcher kagenti.io/protocol=ACP
kubectl label agent acp-ollama-researcher kagenti.io/framework=LangGraph

kubectl label agent acp-weather-service kagenti.io/type=agent
kubectl label agent acp-weather-service kagenti.io/protocol=ACP
kubectl label agent acp-weather-service kagenti.io/framework=LangGraph


:
: -------------------------------------------------------------------------
: "Install Kubernetes UI"
: 
:
helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/
helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard --create-namespace --namespace kubernetes-dashboard
kubectl apply -n kubernetes-dashboard -f ${SCRIPT_DIR}/resources/kube-ui.yaml
echo "Bearer token for kubeUI user"
kubectl -n kubernetes-dashboard create token admin-user
echo "run the command 'kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 8443:443' and access ui at https://localhost:8443"