#!/bin/bash

TAG=$(date +%Y%m%d%H%M%S)
IMAGE_NAME="local/kagenti-ui:${TAG}"

#docker build . --tag local/kagenti-ui:${TAG} --load
#kind load docker-image --name kagenti local/kagenti-ui:${TAG}
#kubectl -n kagenti-system set image deployment/kagenti-ui kagenti-ui-container=local/kagenti-ui:${TAG}
#kubectl rollout status -n kagenti-system deployment/kagenti-ui
#kubectl get -n kagenti-system pod -l app=kagenti-ui

echo "Building image: ${IMAGE_NAME}"
docker build . --tag local/kagenti-ui:${TAG} --load
kind load docker-image --name kagenti local/kagenti-ui:${TAG}

if command -v podman &> /dev/null; then
   echo "Using podman as container runtime"
   kubectl -n kagenti-system set image deployment/kagenti-ui kagenti-ui-container=localhost/local/kagenti-ui:${TAG}

elif command -v docker &> /dev/null; then
    echo "Using docker as container runtime"
    kubectl -n kagenti-system set image deployment/kagenti-ui kagenti-ui-container=local/kagenti-ui:${TAG}

else
    echo "Neither podman nor docker is installed. Please install one of them to build the UI."
    exit 1
fi

echo "Waiting for rollout to complete"
kubectl rollout status -n kagenti-system deployment/kagenti-ui
kubectl get -n kagenti-system pod -l app=kagenti-ui
