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

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
