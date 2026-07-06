# tools/hitl/Makefile
# Project-agnostic entry points for the human-in-the-loop (HITL) policy.
# This is the file-edit / command-control subsystem. It is intentionally
# separate from tools/memory/ (the knowledge-graph subsystem).
#
# Usage:
#   make -f tools/hitl/Makefile protected-list
#   make -f tools/hitl/Makefile protected-check P=opencode.json
#   make -f tools/hitl/Makefile protected-allow P=opencode.json
#   make -f tools/hitl/Makefile install-hooks
#
# Invoked from the project root. The Makefile's own location determines
# paths so `make -C tools/hitl ...` and `cd tools/hitl && make ...`
# also work.

P ?=

# Resolve absolute paths regardless of cwd of make.
HERE := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PROJECT_ROOT := $(abspath $(HERE)../..)
CHECK_EDIT_SH := $(HERE)check-edit.sh

PROTECTED_FILE := $(HERE).protected
ALLOWANCES_FILE := $(HERE).protected-allowances
HOOK_SRC := $(HERE)hooks/pre-commit
HOOK_DST := $(PROJECT_ROOT)/.git/hooks/pre-commit

.PHONY: help protected-list protected-check protected-allow install-hooks uninstall-hooks audit

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

protected-list: ## Print the protected-files list (the files that need human approval to edit).
	@awk '!/^[[:space:]]*(\#|\/\/|<!--.*-->|$$)/ {print}' $(PROTECTED_FILE) | sed 's|^|  |'

protected-check: ## Check whether P (or paths, comma-separated) is allowed. Exits 1 if blocked.
	@test -n "$(P)" || (echo "usage: make -f tools/hitl/Makefile protected-check P=tools/hitl/Makefile[,other]"; exit 2)
	@COMMA=, ; bash $(CHECK_EDIT_SH) $(subst $$COMMA, ,$(P))

protected-allow: ## Add P to .protected-allowances (one-off per-session permission). Logs the grant.
	@test -n "$(P)" || (echo "usage: make -f tools/hitl/Makefile protected-allow P=tools/hitl/Makefile"; exit 2)
	@if ! grep -qxF "$(P)" $(ALLOWANCES_FILE) 2>/dev/null; then \
	  printf '%s\n' "$(P)" >> $(ALLOWANCES_FILE); \
	  echo "added to .protected-allowances: $(P)"; \
	else \
	  echo "already in .protected-allowances: $(P)"; \
	fi
	@mkdir -p $(PROJECT_ROOT)/runs
	@printf '%s\t%s\t%s\n' \
	  "$$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
	  "protected-allow" \
	  "$(P)" \
	  >> $(PROJECT_ROOT)/runs/protected.log
	@echo "logged to runs/protected.log (gitignored)"

install-hooks: ## Install the pre-commit hook into .git/hooks/ (one-time per clone).
	@if [ ! -d $(PROJECT_ROOT)/.git ]; then \
	  echo "no .git/ at $(PROJECT_ROOT) — nothing to install" >&2; \
	  exit 1; \
	fi
	@cp $(HOOK_SRC) $(HOOK_DST)
	@chmod +x $(HOOK_DST)
	@echo "installed $(HOOK_DST)"
	@echo "to remove: rm $(HOOK_DST)"

uninstall-hooks: ## Remove the pre-commit hook from .git/hooks/.
	@if [ -f $(HOOK_DST) ]; then \
	  rm $(HOOK_DST); \
	  echo "removed $(HOOK_DST)"; \
	else \
	  echo "no hook at $(HOOK_DST) — nothing to do"; \
	fi

audit: ## Verify the HITL subsystem is consistent: list exists, hook installed, opencode.json deny rules parse.
	@echo "--- protected list ---"
	@test -f $(PROTECTED_FILE) && echo "OK: $(PROTECTED_FILE) exists" || (echo "MISSING: $(PROTECTED_FILE)" >&2; exit 1)
	@echo "--- pre-commit hook ---"
	@if [ -f $(HOOK_DST) ]; then echo "OK: $(HOOK_DST) installed"; else echo "WARN: $(HOOK_DST) not installed (run: make -f tools/hitl/Makefile install-hooks)"; fi
	@echo "--- opencode.json permission block ---"
	@OC=$(PROJECT_ROOT)/opencode.json; \
	  if [ -f $$OC ]; then \
	    node -e "const c=require('$${OC}'); if(!c.permission) {console.error('MISSING: permission block'); process.exit(1)} console.log('OK: permission block present, edit denies:', Object.keys(c.permission.edit||{}).length, ', bash denies:', Object.keys(c.permission.bash||{}).length)" 2>/dev/null \
	      || echo "WARN: opencode.json present but could not be parsed by node"; \
	  else \
	    echo "WARN: opencode.json not at project root"; \
	  fi
