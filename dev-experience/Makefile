# Paved-road task interface. The point of this file: a developer (or CI, or
# a new hire on day one) runs `make <verb>` and never has to remember the
# per-tool incantation behind it. Local commands and CI call the SAME
# targets, so "passes on my machine" and "passes in CI" stop diverging.
#
# Targets that wrap THIS KIT's tools (doctor, migrations, policy, obs-*) are
# real and work as-is. The app-specific ones (setup/test/lint/fmt) carry a
# TODO — fill in your stack's actual commands once, here, and everyone gets
# them. Run `make help` for the list.

.DEFAULT_GOAL := help
COMPOSE := docker compose
# Path to a clone of platform-starter-kit, for `make sync`. Override:
#   make sync KIT_PATH=/path/to/platform-starter-kit
KIT_PATH ?= ../platform-starter-kit

.PHONY: help setup run up down test lint fmt scan doctor migrations policy obs-up obs-down sync

help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies + git hooks (fill in your stack's installs)
	# TODO: e.g. `pip install -e ".[dev]"` or `npm ci` — see docs/TECH-STACK-SWAP-GUIDE.md
	@command -v detect-secrets >/dev/null 2>&1 && { [ -f .secrets.baseline ] || detect-secrets scan > .secrets.baseline; } || true
	@command -v pre-commit >/dev/null 2>&1 && pre-commit install || echo "pre-commit not installed — skipping hook install"

run: up ## Alias for `up`

up: ## Start the app stack locally
	$(COMPOSE) up -d

down: ## Stop the app stack
	$(COMPOSE) down

test: ## Run the test suite (fill in your stack's test command)
	# TODO: e.g. `pytest` or `npm test`
	@echo "Set the test command in the Makefile's 'test' target."

lint: ## Run linters (fill in, or rely on pre-commit)
	@command -v pre-commit >/dev/null 2>&1 && pre-commit run --all-files || echo "TODO: set your linter command"

fmt: ## Auto-format the codebase (fill in your formatter)
	# TODO: e.g. `ruff format . && isort .` or `prettier --write .`
	@echo "Set the formatter command in the Makefile's 'fmt' target."

scan: ## Run local security scans (uses security/ scripts if present)
	@if [ -f security/manual-checks.sh ]; then bash security/manual-checks.sh; \
	else echo "No security/manual-checks.sh — see the security/ folder or docs/."; fi

doctor: ## Readiness check against this repo (tools/doctor.py)
	@python3 tools/doctor.py .

migrations: ## Check DB migrations for backward-incompatible changes
	@python3 tools/check_migrations.py

policy: ## Run policy-as-code against a Terraform plan (needs conftest + a plan.json)
	@if [ -d governance/policy-as-code ]; then \
		echo "Generate a plan first: (cd iac-terraform/<module> && terraform show -json plan.binary > plan.json)"; \
		echo "then: conftest test --policy governance/policy-as-code/policy plan.json"; \
	else echo "No governance/policy-as-code — skipping."; fi

obs-up: ## Start observability (layers on YOUR app's docker-compose.yml — add that first)
	@[ -f docker-compose.yml ] || { echo "No docker-compose.yml here. The observability stack layers on top of your app's compose file — add a docker-compose.yml for your service first (see observability/docker-compose.observability.yml's usage comment)."; exit 1; }
	@[ -d observability ] || { echo "No observability/ here — scaffold with observability enabled, or copy the folder in."; exit 1; }
	$(COMPOSE) -f docker-compose.yml -f observability/docker-compose.observability.yml --profile observability up -d

obs-down: ## Stop the observability stack
	@[ -f docker-compose.yml ] && [ -d observability ] || { echo "Nothing to stop — no docker-compose.yml + observability/ here."; exit 0; }
	$(COMPOSE) -f docker-compose.yml -f observability/docker-compose.observability.yml --profile observability down -v

sync: ## Report upstream kit changes since you scaffolded (set KIT_PATH=path/to/kit)
	@[ -d "$(KIT_PATH)/tools" ] || { echo "Kit not found at KIT_PATH=$(KIT_PATH). Point it at your platform-starter-kit checkout: make sync KIT_PATH=/path/to/platform-starter-kit"; exit 1; }
	@python3 tools/sync_check.py . --kit-path $(KIT_PATH) --show-diffs
