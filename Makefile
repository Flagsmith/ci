help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install-packages
install-packages: ## Install all required packages
	uv sync $(or $(opts),'--all-extras')

.PHONY: install-pre-commit
install-pre-commit: ## Install pre-commit hooks
	uv run pre-commit install

.PHONY: install
install: install-packages install-pre-commit ## Ensure the environment is set up

.PHONY: lint
lint: ## Run linters
	uv run --all-extras pre-commit run --all-files

.PHONY: test
test: ## Run tests
	uv run pytest $(opts)

.PHONY: generate-code-references-types
generate-code-references-types: ## Generate code_references types from Flagsmith API schema
	@curl -sSL https://api.flagsmith.com/api/v1/swagger.json | \
	npx --yes --quiet openapi-format /dev/fd/0 --no-bundle --filterFile src/code_references/openapi-filter.yaml 2>/dev/null | \
	uvx --from 'datamodel-code-generator[ruff]' datamodel-codegen \
		--output src/code_references/types.py \
		--output-model-type typing.TypedDict \
		--target-python-version 3.14 \
		--use-double-quotes \
		--use-standard-collections \
		--remove-special-field-name-prefix \
		--input-file-type openapi \
		--disable-timestamp \
		--formatters ruff-check ruff-format
