# agents/memory/scripts/Makefile
# Project-agnostic entry points for the memory infrastructure.
# The agent that bootstraps the project writes the project name to
# agents/memory/.project (a single line — the Neo4j group_id). Every target
# resolves PROJECT from there. Override on a single command with
# `make seed PROJECT=foo`.
#
# Usage:
#   make -f agents/memory/scripts/Makefile set-project PROJECT=malariasentinel  # one-time
#   make -f agents/memory/scripts/Makefile bootstrap                            # cold start
#   make -f agents/memory/scripts/Makefile seed                                # idempotent
#   make -f agents/memory/scripts/Makefile audit                               # invariants
#
# Invoked from the project root. The Makefile's own location determines
# paths so `make -C agents/memory/scripts ...` and
# `cd agents/memory/scripts && make ...` also work.

PROJECT ?= malariasentinel
CYPHER  ?=

PROJECT_FILE := $(abspath $(HERE)../.project)

# Resolve PROJECT: env override > file > empty (most targets fail clearly).
ifdef PROJECT
  PROJECT_RESOLVED := $(PROJECT)
else
  PROJECT_RESOLVED := $(shell test -f $(PROJECT_FILE) && cat $(PROJECT_FILE) | tr -d '[:space:]')
endif

.PHONY: help status up down bootstrap seed bootstrap-apply audit query wipe schema-labels clean-schema-cache set-project show-project session-start session-end

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

show-project: ## Print the resolved project (group_id).
	@if [ -z "$(PROJECT_RESOLVED)" ]; then \
	  echo "no project set"; \
	  echo "  fix: make -f agents/memory/scripts/Makefile set-project PROJECT=name"; \
	  exit 1; \
	fi
	@echo "$(PROJECT_RESOLVED)"

set-project: ## Set the project name (writes agents/memory/.project). Usage: make set-project PROJECT=name
	@if [ -z "$(PROJECT)" ]; then \
	  echo "usage: make -f agents/memory/scripts/Makefile set-project PROJECT=name" >&2; \
	  exit 2; \
	fi
	@echo "$(PROJECT)" > $(PROJECT_FILE)
	@echo "wrote $(PROJECT_FILE) -> $(PROJECT)"

# --- project-agnostic helpers (defined once, used by every target) ---
define require_project
	@if [ -z "$(PROJECT_RESOLVED)" ]; then \
	  echo "no project set — run: make -f agents/memory/scripts/Makefile set-project PROJECT=name" >&2; \
	  echo "  or override: make ... PROJECT=name" >&2; \
	  exit 2; \
	fi
endef

# Resolve absolute paths regardless of cwd of make.
HERE := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PROJECT_ROOT := $(abspath $(HERE)../../..)
MEMORY_SH := $(HERE)memory.sh
SEED_SH   := $(HERE)seed.sh
SCHEMA_SH := $(HERE)schema.sh

status: ## Stack health: docker + neo4j-cli + graphiti.
	bash $(MEMORY_SH) status

up: ## Start Neo4j + Graphiti MCP containers.
	cd $(PROJECT_ROOT)/agents/memory/runtime && docker compose up -d

down: ## Stop Neo4j + Graphiti MCP containers.
	cd $(PROJECT_ROOT)/agents/memory/runtime && docker compose down

bootstrap: up status seed bootstrap-apply audit ## Cold start: up + status + seed + bootstrap-apply + audit. Use this on a fresh clone.

seed: ## Seed the graph for PROJECT. Requires set-project first (or override).
	$(require_project)
	bash $(SEED_SH) $(PROJECT_RESOLVED)

bootstrap-apply: ## Apply all agents/memory/scripts/bootstrap/*.yaml as one atomic write. Idempotent; safe to run on every session.
	$(require_project)
	bash $(HERE)bootstrap-apply.sh $(PROJECT_RESOLVED)

audit: ## Run the three schema invariants. Exits 1 on any failure.
	$(require_project)
	GROUP_ID=$(PROJECT_RESOLVED) bash $(MEMORY_SH) audit

query: ## Run a Cypher query. Pass with CYPHER="MATCH (n) RETURN n".
	@test -n "$(CYPHER)" || (echo "usage: make query CYPHER='MATCH ...'"; exit 2)
	bash $(MEMORY_SH) query "$(CYPHER)"

wipe: ## Wipe all data for PROJECT. DESTRUCTIVE — backs up to /tmp first.
	$(require_project)
	@bash -c 'set -e; \
	  ts=$$(date +%Y%m%d-%H%M%S); \
	  cd $(PROJECT_ROOT)/agents/memory/runtime && \
	  neo4j-cli query "MATCH (n) WHERE n.group_id=\"$(PROJECT_RESOLVED)\" RETURN n.uuid, n.name, labels(n)" --format json > "/tmp/$(PROJECT_RESOLVED)-wipe-$$ts.json" && \
	  echo "backup: /tmp/$(PROJECT_RESOLVED)-wipe-$$ts.json" && \
	  neo4j-cli query "MATCH (n) WHERE n.group_id=\"$(PROJECT_RESOLVED)\" DETACH DELETE n" --rw --atomic && \
	  echo "wiped group_id=$(PROJECT_RESOLVED)"'

schema-labels: ## Print the 9 schema labels (8 real + 1 graphiti-core compat).
	bash $(MEMORY_SH) schema labels

clean-schema-cache: ## Remove the parsed-schema cache so it regenerates on next call.
	@rm -f $(PROJECT_ROOT)/runs/schema.cache
	@echo "schema.cache removed; will rebuild on next memory.sh call"

session-start: ## Run the session-start routine: audit + project-state queries. Run at the start of every session that touches the project.
	$(require_project)
	@bash $(HERE)session-start.sh "$(PROJECT_RESOLVED)"

session-end: ## Print a session-end checklist (what to update, what to write). Run before stopping.
	@bash $(HERE)session-end.sh
