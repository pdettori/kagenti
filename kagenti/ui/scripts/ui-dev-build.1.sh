#!/bin/bash

#TAG=$(date +%Y%m%d%H%M%S)
#docker build . --tag local/kagenti-ui:${TAG} --load
#kind load docker-image --name kagenti local/kagenti-ui:${TAG}
#kubectl -n kagenti-system set image deployment/kagenti-ui kagenti-ui-container=local/kagenti-ui:${TAG}
#kubectl rollout status -n kagenti-system deployment/kagenti-ui
#kubectl get -n kagenti-system pod -l app=kagenti-ui


set -euo pipefail

TAG=$(date +%Y%m%d%H%M%S)
IMAGE=local/kagenti-ui:${TAG}
KIND_CLUSTER=kagenti
NAMESPACE=kagenti-system
DEPLOYMENT=kagenti-ui
CONTAINER=kagenti-ui-container

echo "🔨 Building image ${IMAGE}"
docker build -t ${IMAGE} .

echo "📦 Loading image into kind cluster"
kind load docker-image --name ${KIND_CLUSTER} ${IMAGE}

echo "🚀 Updating deployment image"
kubectl -n ${NAMESPACE} set image deployment/${DEPLOYMENT} \
  ${CONTAINER}=${IMAGE}

echo "⏳ Waiting for rollout"
kubectl rollout status -n ${NAMESPACE} deployment/${DEPLOYMENT}

echo "✅ Pods:"
kubectl get -n ${NAMESPACE} pod -l app=kagenti-ui
