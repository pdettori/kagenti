.PHONY: lint
lint:
	cd kagenti/ui; uv run pylint Home.py pages/*.py lib/*.py

# Define the path for the output file
PRELOAD_FILE := deployments/ansible/kind/preload-images.txt

# The primary task to list and filter images
preload-file:
	@mkdir -p $$(dirname $(PRELOAD_FILE)) && \
	kubectl get pods --all-namespaces -o json | jq -r '.items[] | (.spec.containers // [])[].image, (.spec.initContainers // [])[].image' | sort -u | grep -E '^(docker\.io/|[^./]+/[^./])' | \
 	tee $(PRELOAD_FILE)  && \
 	echo "Filtered local and docker.io images have been saved to $(PRELOAD_FILE)"
.PHONY: preload-file