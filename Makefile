.PHONY: lint
lint:
	cd kagenti/ui; uv run pylint Home.py pages/*.py lib/*.py

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