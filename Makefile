.PHONY: setup test clean lint format run help

# Global variables
# Detect if we are on Windows or Linux/Mac
ifeq ($(OS),Windows_NT)
    PYTHON := python
    VENV := .venv
    VENV_PYTHON := $(VENV)/Scripts/python.exe
    VENV_PIP := $(VENV)/Scripts/pip.exe
else
    PYTHON := python3
    VENV := .venv
    VENV_PYTHON := $(VENV)/bin/$(PYTHON)
    VENV_PIP := $(VENV)/bin/$(PIP)
endif


help: ## Show this help menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## First-time setup: creates virtualenv, installs all requirements (prod, test), and configures pre-commit
	@echo "=> Creating Python virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "=> Upgrading pip..."
	$(VENV_PIP) install --upgrade pip
	@echo "=> Installing project dependencies..."
	$(VENV_PIP) install -r requirements.txt
	@echo "=> Installing test dependencies..."
	$(VENV_PIP) install -r tests/requirements.txt
	@echo "=> Installing pre-commit hooks..."
	$(VENV_PYTHON) -m pre_commit install
	@echo "=> (Optional) Installing Playwright browsers..."
	$(VENV_PYTHON) -m playwright install chromium
	@echo "\n✅ Setup complete! Activate the environment using: source .venv/bin/activate (or .venv\\Scripts\\activate on Windows)"

test: ## Run the pytest test suite
	$(VENV_PYTHON) -m pytest tests/

lint: ## Run flake8 and pre-commit checks on all files
	$(VENV_PYTHON) -m pre_commit run --all-files

format: ## Run black to auto-format Python files
	$(VENV_PYTHON) -m black .

run: ## Run the scraper script locally
	cd scripts && ../$(VENV_PYTHON) update_jobs.py

clean: ## Remove virtualenv, caches, and build artifacts
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf scripts/__pycache__
	rm -rf tests/__pycache__
	@echo "Cleaned up all temporary files."
