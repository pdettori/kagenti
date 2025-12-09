#!/usr/bin/env bash
set -euo pipefail

# Timestamp tag
TAG=$(date +%Y%m%d%H%M%S)
INTENDED="local/kagenti-ui:${TAG}"

detect_impl() {
  # Allow explicit override
  if [ -n "${DOCKER_IMPL-}" ]; then
    printf '%s\n' "${DOCKER_IMPL}"
    return
  fi

  # Try podman first if present
  if command -v podman >/dev/null 2>&1; then
    out=$(podman info 2>/dev/null || true)
    if printf '%s' "$out" | grep -Ei 'apiversion|buildorigin|libpod|podman|version:' >/dev/null 2>&1; then
      printf 'podman\n'
      return
    fi
  fi

  # Try docker
  if command -v docker >/dev/null 2>&1; then
    out=$(docker info 2>/dev/null || true)
    # If docker info looks like Docker Engine, classify as docker
    if printf '%s' "$out" | grep -Ei 'client: docker engine|docker engine - community|server:' >/dev/null 2>&1; then
      printf 'docker\n'
      return
    fi
    # If docker info contains podman/libpod markers, it's actually Podman (symlink case)
    if printf '%s' "$out" | grep -Ei 'apiversion|buildorigin|libpod|podman|version:' >/dev/null 2>&1; then
      printf 'podman\n'
      return
    fi
  fi

  printf 'unknown\n'
}

DETECTED=$(detect_impl)
echo "Detected implementation: ${DETECTED}"

echo "Building image ${INTENDED} ..."
docker build . -t "${INTENDED}" --load

# Discover the actual repo:tag created for our TAG
image_ref=$(docker images --filter=reference="*:${TAG}" --format '{{.Repository}}:{{.Tag}}' | head -n1 || true)

# If no repo:tag found, try lookup by image ID and inspect RepoTags
if [ -z "${image_ref}" ]; then
  image_id=$(docker images --filter=reference="*:${TAG}" --format '{{.ID}}' | head -n1 || true)
  if [ -n "${image_id}" ]; then
    image_ref=$(docker image inspect "${image_id}" --format '{{index .RepoTags 0}}' 2>/dev/null || true)
  fi
fi

# Last resort: use intended name
if [ -z "${image_ref}" ]; then
  echo "Warning: could not discover produced image tag; falling back to ${INTENDED}"
  image_ref="${INTENDED}"
fi

echo "Image discovered: ${image_ref}"

# If image_ref is prefixed with localhost/, make a non-localhost alternate (useful when podman produced localhost/...)
alt_ref=""
if printf '%s' "${image_ref}" | grep -q '^localhost/'; then
  alt_ref="${image_ref#localhost/}"
  if ! docker image inspect "${alt_ref}" >/dev/null 2>&1; then
    echo "Tagging ${image_ref} -> ${alt_ref}"
    docker tag "${image_ref}" "${alt_ref}"
  fi
fi

# Load image(s) into kind
echo "Loading ${image_ref} into kind (cluster: agent-platform)..."
kind load docker-image --name kagenti "${image_ref}"

if [ -n "${alt_ref}" ]; then
  echo "Also loading ${alt_ref} into kind..."
  kind load docker-image --name kagenti "${alt_ref}"
fi

# Prefer alt_ref for kubernetes if present (most manifests assume no localhost/)
k8s_image="${alt_ref:-${image_ref}}"
echo "Updating k8s deployment to use image: ${k8s_image}"
kubectl -n kagenti-system set image deployment/kagenti-ui kagenti-ui-container="${k8s_image}"
kubectl rollout status -n kagenti-system deployment/kagenti-ui
kubectl get -n kagenti-system pod -l app=kagenti-ui
