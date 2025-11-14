.PHONY: lint
lint:
	cd kagenti/ui; uv run pylint Home.py pages/*.py lib/*.py

# Define variables
AGENT_OAUTH_SECRET_IMAGE := agent-oauth-secret
AGENT_OAUTH_SECRET_DIR := kagenti/auth/agent-oauth-secret
KIND_CLUSTER_NAME := kagenti
# Generate unique tag using git commit hash (short) or timestamp if not in git repo
AGENT_OAUTH_SECRET_TAG := $(shell git rev-parse --short HEAD 2>/dev/null | xargs -I {} sh -c 'echo "{}-$$(date +%s)"' || date +%s)

# Build and load agent-oauth-secret image into kind cluster for testing
.PHONY: build-load-agent-oauth-secret
build-load-agent-oauth-secret:
	@echo "Building $(AGENT_OAUTH_SECRET_IMAGE):$(AGENT_OAUTH_SECRET_TAG) image..."
	docker build -t $(AGENT_OAUTH_SECRET_IMAGE):$(AGENT_OAUTH_SECRET_TAG) $(AGENT_OAUTH_SECRET_DIR) --load
	@echo "Loading $(AGENT_OAUTH_SECRET_IMAGE):$(AGENT_OAUTH_SECRET_TAG) image into kind cluster $(KIND_CLUSTER_NAME)..."
	kind load docker-image $(AGENT_OAUTH_SECRET_IMAGE):$(AGENT_OAUTH_SECRET_TAG) --name $(KIND_CLUSTER_NAME)
	@echo "✓ $(AGENT_OAUTH_SECRET_IMAGE):$(AGENT_OAUTH_SECRET_TAG) image built and loaded successfully"
	@echo ""
	@echo "To use this image, update your deployment with:"
	@echo "  image: $(AGENT_OAUTH_SECRET_IMAGE):$(AGENT_OAUTH_SECRET_TAG)"

# Define the path for the output file
PRELOAD_FILE := deployments/ansible/kind/preload-images.txt

# The primary task to list and filter images
.PHONY: preflight-check preload-file

# Verify required commands are available before running other targets
preflight-check:
	@# fail fast with a helpful message if any required command is missing
	@( for cmd in kubectl jq; do \
		if ! command -v $$cmd >/dev/null 2>&1; then \
			echo >&2 "ERROR: '$$cmd' not found. Please install it (for example: 'brew install $$cmd' on macOS) and retry."; \
			exit 1; \
		fi; \
		done )

# The primary task to list and filter images; depend on the preflight check
preload-file: preflight-check
	@mkdir -p $$(dirname $(PRELOAD_FILE)) && \
	kubectl get pods --all-namespaces -o json | jq -r '.items[] | (.spec.containers // [])[].image, (.spec.initContainers // [])[].image' | sort -u | grep -E '^(docker\.io/|[^./]+/[^./])' | \
	tee $(PRELOAD_FILE) && \
	echo "Filtered local and docker.io images have been saved to $(PRELOAD_FILE)"