#!/bin/bash

ENABLE_OPENSHIFT=${ENABLE_OPENSHIFT:-true}
GATEWAY_API_ENABLED=${GATEWAY_API_ENABLED:-true}
ISTIO_ENABLED=${ISTIO_ENABLED:-true}
KIALI_ENABLED=${KIALI_ENABLED:-true}
CERT_MANAGER_ENABLED=${CERT_MANAGER_ENABLED:-true}
SPIRE_ENABLED=${SPIRE_ENABLED:-true}
KEYCLOAK_ENABLED=${KEYCLOAK_ENABLED:-true}
OTEL_ENABLED=${OTEL_ENABLED:-true}
SPIRE_ENABLED=${SPIRE_ENABLED:-true}
MCP_INSPECTOR_ENABLED=${MCP_INSPECTOR_ENABLED:-true}
METRICS_SERVER_ENABLED=${METRICS_SERVER_ENABLED:-true}
TEKTON_ENABLED=${TEKTON_ENABLED:-true}
INGRESS_GATEWAY_ENABLED=${INGRESS_GATEWAY_ENABLED:-true}
TOOLHIVE_ENABLED=${TOOLHIVE_ENABLED:-true}

CREATE_KIND_CLUSTER=${CREATE_KIND_CLUSTER:-true}
KIND_CLUSTER_NAME=${KIND_CLUSTER_NAME:-kagenti}
KIND_CONTAINER_REGISTRY_ENABLED=${KIND_CONTAINER_REGISTRY_ENABLED:-true}
KIND_IMAGES_PRELOAD=${KIND_IMAGES_PRELOAD:-false}

# utils

# Get the path used to execute the script (may be relative or a symlink)
SOURCE="${BASH_SOURCE[0]}"

# Loop to resolve symlinks until the original file is found
while [ -h "$SOURCE" ]; do # Check if SOURCE is a symbolic link (-h)
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  # If $SOURCE was a relative symlink, we need to resolve it relative to its directory
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" 
done

# Get the absolute directory of the script
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

# Function to read a list of image paths from a file and load them into a KIND cluster.
#
# Usage: kind_load_images <image_list_file_path> <cluster_name>
#
# Arguments:
#   $1 (required): Path to the text file containing the image list.
#   $2 (required): The name of the target KIND cluster.
#
kind_load_images() {
    # Assign positional arguments to meaningful local variables
    local IMAGE_LIST_FILE="$1"
    local CLUSTER_NAME="$2"

    # Check for required arguments
    if [ -z "$IMAGE_LIST_FILE" ] || [ -z "$CLUSTER_NAME" ]; then
        echo "Error: Both image list file and cluster name must be provided." >&2
        echo "Usage: kind_load_images <image_list_file_path> <cluster_name>" >&2
        return 1
    fi

    # Check if the image list file exists
    if [ ! -f "$IMAGE_LIST_FILE" ]; then
        echo "Error: Image list file '$IMAGE_LIST_FILE' not found." >&2
        return 1
    fi

    echo "--- Starting KIND Image Preload for cluster: $CLUSTER_NAME from file: $IMAGE_LIST_FILE ---"

    # Read the file line by line
    # -r: Prevents backslash escapes from being interpreted
    # IFS=: Ensures leading/trailing whitespace is preserved initially (but we strip it later)
    while IFS= read -r LINE
    do
        # Use BASH Parameter Expansion and command substitution to strip leading/trailing whitespace
        IMAGE_NAME=$(echo "$LINE" | xargs)

        # Skip lines that are empty or start with '#' (comments)
        if [[ -z "$IMAGE_NAME" || "$IMAGE_NAME" =~ ^# ]]; then
            continue
        fi

        # Execute the kind load command
        echo "Attempting to load image: $IMAGE_NAME"
        kind load docker-image "$IMAGE_NAME" --name "$CLUSTER_NAME"

        # Check the exit status of the kind command
        if [ $? -eq 0 ]; then
            echo "Successfully loaded $IMAGE_NAME"
        else
            echo "Warning: Failed to load $IMAGE_NAME (Exit Code: $?). It might not be pulled locally." >&2
        fi
    done < "$IMAGE_LIST_FILE"

    echo "--- Image loading process complete ---"
}

# start installation

# check if connected to an OpenShift cluster
if kubectl api-resources 2>/dev/null | grep -q "openshift.io"; then
  echo "OpenShift cluster detected"
  ENABLE_OPENSHIFT=true
else
  if kubectl version --client 2>/dev/null 1>/dev/null; then
    # kubectl ran successfully (at least the client part), but 'openshift.io' was not found.
    echo "Standard Kubernetes cluster detected"
    ENABLE_OPENSHIFT=false
  else
    # kubectl failed (likely no connection)
    echo "Error: No connected cluster found."
    ENABLE_OPENSHIFT=false

    # Exit if CREATE_KIND_CLUSTER is also false
    if [ "$CREATE_KIND_CLUSTER" = "false" ]; then
      echo "Exiting because no cluster is connected and CREATE_KIND_CLUSTER is false."
      exit 1
    fi
  fi

  if [ "$CREATE_KIND_CLUSTER" = "true" ]; then
    if kind get clusters 2>/dev/null | grep -q "^${KIND_CLUSTER_NAME}$"; then
        echo "kind cluster exists, nothing to be done"
    else
       if [ "$KIND_CONTAINER_REGISTRY_ENABLED" = "true" ]; then 
            kind create cluster --name ${KIND_CLUSTER_NAME} --config="${SCRIPT_DIR}/kind-config-registry.yaml"
        else
            kind create cluster --name ${KIND_CLUSTER_NAME} --config="${SCRIPT_DIR}/kind-config.yaml"
        fi    
    fi

    if [ "$KIND_IMAGES_PRELOAD" = "true" ]; then
      kind_load_images ${SCRIPT_DIR}/preload-images.txt ${KIND_CLUSTER_NAME}
    fi
  fi  

  if [ "$ISTIO_ENABLED" = "true" ]; then
    # install istio
    helm repo add istio https://istio-release.storage.googleapis.com/charts
    helm repo update

    helm upgrade --install istio-base istio/base -n istio-system --create-namespace --wait

    helm  upgrade --install istiod istio/istiod --namespace istio-system --set profile=ambient --wait

    helm  upgrade --install istio-cni istio/cni -n istio-system --set profile=ambient --wait

    helm upgrade --install ztunnel istio/ztunnel -n istio-system

    kubectl label ns istio-system shared-gateway-access=true

    if [ "$KIALI_ENABLED" = "true" ]; then
        kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.27/samples/addons/prometheus.yaml

        kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.27/samples/addons/kiali.yaml
    fi
  fi

   if [ "$CERT_MANAGER_ENABLED" = "true" ]; then
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.17.2/cert-manager.yaml
  fi

  if [ "$SPIRE_ENABLED" = "true" ]; then
    helm upgrade --install spire-crds spire-crds -n spire-mgmt --repo https://spiffe.github.io/helm-charts-hardened/ --create-namespace --wait
    helm upgrade --install spire spire -n spire-mgmt --repo https://spiffe.github.io/helm-charts-hardened/ -f "${SCRIPT_DIR}/spire-helm-values.yaml"
  fi  

fi

if [ "$GATEWAY_API_ENABLED" = "true" ]; then
# if not found, install the gateway CRD
kubectl get crd gateways.gateway.networking.k8s.io &> /dev/null || \
  kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.3.0/standard-install.yaml
fi

# install kagenti-deps chart

echo "installing kagenti-deps chart"

helm dependency update ${SCRIPT_DIR}/../../charts/kagenti-deps/
helm upgrade --install kagenti-deps ${SCRIPT_DIR}/../../charts/kagenti-deps/ -n kagenti-system --create-namespace \
--set openshift=${ENABLE_OPENSHIFT} \
--set components.istio.enabled=${ISTIO_ENABLED} \
--set components.kiali.enabled=${KIALI_ENABLED} \
--set components.keycloak.enabled=${KEYCLOAK_ENABLED} \
--set components.otel.enabled=${OTEL_ENABLED} \
--set components.spire.enabled=${SPIRE_ENABLED} \
--set components.mcpInspector.enabled=${MCP_INSPECTOR_ENABLED} \
--set components.metricsServer.enabled=${METRICS_SERVER_ENABLED} \
--set components.containerRegistry.enabled=${KIND_CONTAINER_REGISTRY_ENABLED} \
--set components.tekton.enabled=${TEKTON_ENABLED} \
--set components.certManager.enabled=${CERT_MANAGER_ENABLED} \
--set components.gatewayApi.enabled=${GATEWAY_API_ENABLED} \
--set components.ingressGateway.enabled=${INGRESS_GATEWAY_ENABLED} \
--set components.toolhive.enabled=${TOOLHIVE_ENABLED} \

# install main kagenti chart

echo "installing kagenti chart"

helm dependency update ${SCRIPT_DIR}/../../charts/kagenti/
LATEST_TAG=$(git ls-remote --tags --sort="v:refname" https://github.com/kagenti/kagenti.git | tail -n1 | sed 's|.*refs/tags/||; s/\^{}//')

helm upgrade --install kagenti ${SCRIPT_DIR}/../../charts/kagenti/ -n kagenti-system --create-namespace -f ${SCRIPT_DIR}/../../charts/kagenti/.secrets.yaml --set ui.tag=${LATEST_TAG} \
--set openshift=${ENABLE_OPENSHIFT} 





