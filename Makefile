
.PHONY: lint
lint:
	pylint kagenti/ui/pages/*.py kagenti/ui/*.py kagenti/ui/lib/*.py
