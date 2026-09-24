.PHONY: help setup install lock test lint format typecheck run clean site-dev site-build site-test

# Global variables
PYTHON := python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
UV := uv

help: ## Show this help menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## First-time setup: virtualenv, hash-locked deps (runtime + dev), pre-commit hook
	@echo "=> Creating Python virtual environment..."
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(MAKE) install
	@echo "=> Installing pre-commit hooks..."
	$(VENV_PYTHON) -m pre_commit install
	@echo "\n✅ Setup complete! Activate the environment using: source .venv/bin/activate (or .venv\\Scripts\\activate on Windows)"

install: ## Install hash-locked runtime + dev dependencies into .venv
	$(VENV_PYTHON) -m pip install --require-hashes -r requirements.txt -r requirements-dev.txt
	$(VENV_PYTHON) -m pip install -e . --no-deps

lock: ## Regenerate requirements*.txt from pyproject.toml (needs uv)
	$(UV) pip compile pyproject.toml --generate-hashes --python-version 3.11 --universal -o requirements.txt
	$(UV) pip compile pyproject.toml --extra dev -c requirements.txt --generate-hashes --python-version 3.11 --universal -o requirements-dev.txt

test: ## Run the pytest test suite (coverage floor enforced via pyproject)
	$(VENV_PYTHON) -m pytest tests/

lint: ## Run ruff and all pre-commit checks on all files
	$(VENV_PYTHON) -m ruff check
	$(VENV_PYTHON) -m pre_commit run --all-files

format: ## Apply ruff's safe autofixes (import sorting, pyupgrade, etc.)
	$(VENV_PYTHON) -m ruff check --fix

typecheck: ## Run mypy (non-strict) over scripts/
	$(VENV_PYTHON) -m mypy

run: ## Run the scraper locally (writes to $$NGJ_OUTPUT_DIR, default site/public)
	cd scripts && ../$(VENV_PYTHON) update_jobs.py

site-dev: ## Start the site dev server (site/)
	cd site && npm run dev

site-build: ## Build the site (site/dist)
	cd site && npm ci && npm run build

site-test: ## Run the site test suite
	cd site && npm test

clean: ## Remove virtualenv, caches, and build artifacts
	rm -rf $(VENV)
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf .coverage coverage.xml htmlcov *.egg-info
	rm -rf site/dist
	find . -name __pycache__ -type d -not -path './.git/*' -prune -exec rm -rf {} +
	@echo "Cleaned up all temporary files."
