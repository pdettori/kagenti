#!/bin/bash

TAG=$(date +%Y%m%d%H%M%S)
IMAGE_NAME="local/kagenti-ui:${TAG}"
echo "Building image: ${IMAGE_NAME}"
docker build . --tag ${IMAGE_NAME} --load
kind load docker-image --name kagenti local/kagenti-ui:${TAG}

if command -v podman &> /dev/null; then
   echo "Using podman as container runtime - Loading image into kind cluster"
   kubectl -n kagenti-system set image deployment/kagenti-ui kagenti-ui-container=localhost/${IMAGE_NAME}

elif command -v docker &> /dev/null; then
    echo "Using docker as container runtime - Loading image into kind cluster"
    kubectl -n kagenti-system set image deployment/kagenti-ui kagenti-ui-container=${IMAGE_NAME}

else
    echo "Neither podman nor docker is installed. Please install one of them to build the UI."
    exit 1
fi

echo "Waiting for rollout to complete"
kubectl rollout status -n kagenti-system deployment/kagenti-ui
kubectl get -n kagenti-system pod -l app=kagenti-ui
