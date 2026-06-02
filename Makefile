# crtx spec repo — local + CI tooling
#
# All targets are idempotent and run from the repo root. CI mirrors these
# targets in .github/workflows/validate.yml; keep them in sync.

PYTHON ?= python3
MARKDOWNLINT ?= markdownlint-cli2

PY_DEPS := jsonschema[format]==4.25.1
MD_GLOBS := **/*.md \#node_modules \#specs/v*/examples/**

.PHONY: help lint lint-md lint-schema test-scripts ci check-tools

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

lint: lint-md lint-schema ## Run every linter (markdown + JSON schema).

lint-md: ## Lint markdown via markdownlint-cli2.
	@command -v $(MARKDOWNLINT) >/dev/null 2>&1 || { \
		echo "error: $(MARKDOWNLINT) not found"; \
		echo "install: npm install --global markdownlint-cli2"; \
		exit 1; \
	}
	$(MARKDOWNLINT) $(MD_GLOBS)

lint-schema: ## Validate JSON schemas and example envelopes/events.
	@$(PYTHON) -c 'import jsonschema' >/dev/null 2>&1 || { \
		echo "error: python jsonschema not installed"; \
		echo "install: $(PYTHON) -m pip install '$(PY_DEPS)'"; \
		exit 1; \
	}
	$(PYTHON) .github/scripts/validate_specs.py

test-scripts: ## Run unit tests for .github/scripts.
	$(PYTHON) -m unittest discover -s .github/scripts/tests -v

ci: lint test-scripts ## Run everything CI runs (lint + tests).

check-tools: ## Report which tools are installed.
	@printf 'python:        '; command -v $(PYTHON) || echo MISSING
	@printf 'jsonschema:    '; $(PYTHON) -c 'import jsonschema; print(jsonschema.__version__)' 2>/dev/null || echo MISSING
	@printf 'markdownlint:  '; command -v $(MARKDOWNLINT) || echo MISSING
