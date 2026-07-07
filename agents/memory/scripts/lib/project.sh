#!/usr/bin/env bash
# Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.

# agents/memory/scripts/lib/project.sh
# Shared helper to resolve the project name (group_id) for any write.
# Sourced by add-node.sh, add-rel.sh, audit.sh, and any future tool.
#
# Resolution order (first non-empty wins):
#   1. $1 if passed in (CLI override), e.g. resolve_project "$arg"
#   2. $GROUP_ID env var (one-off env override)
#   3. agents/memory/.project (single line, the group_id)
# On miss: prints a clear message to stderr and returns 1.
#
# Usage:
#   resolve_project                       # uses 2 then 3
#   resolve_project "myproject"           # explicit override
#   resolve_project "" && echo "$GROUP_ID" # check then use

resolve_project() {
  local arg="${1:-}"

  if [ -n "$arg" ]; then
    GROUP_ID="$arg"
  elif [ -n "${GROUP_ID:-}" ]; then
    : # env already set
  elif [ -f "${PROJECT_FILE:-agents/memory/.project}" ]; then
    GROUP_ID="$(tr -d '[:space:]' < "$PROJECT_FILE")"
  fi

  if [ -z "${GROUP_ID:-}" ]; then
    echo "no project set" >&2
    echo "  fix one of:" >&2
    echo "    GROUP_ID=foo $0                  # one-off env" >&2
    echo "    echo foo > agents/memory/.project  # persistent" >&2
    return 1
  fi
  export GROUP_ID
  return 0
}

# Anchor for the .project file when the helper is sourced from a script
# that lives in agents/memory/scripts/. The script that sources us should set
# PROJECT_FILE explicitly if it lives elsewhere.
: "${PROJECT_FILE:=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.project}"
