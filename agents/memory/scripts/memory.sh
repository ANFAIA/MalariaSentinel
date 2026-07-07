#!/usr/bin/env bash
# Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.

# agents/memory/scripts/memory.sh
# The single entry point for the project memory infrastructure.
#
# Usage:
#   memory.sh schema                                       # list schema labels
#   memory.sh schema describe <Label>                      # describe one label
#   memory.sh node  --type <L> --uuid <id> --name <n> --summary <s> [--path <p>]
#   memory.sh rel   --type <R> --src <uuid> --dst <uuid> [--prop k=v ...]
#   memory.sh query "<cypher>"                            # arbitrary read or write
#   memory.sh seed <project>                              # seed from seed/<project>.yaml
#   memory.sh audit                                       # run the 3 invariants
#   memory.sh status                                      # docker + neo4j-cli + graphiti
#
# This script is a thin dispatcher. The real work lives in the sibling
# scripts (schema.sh, add-node.sh, add-rel.sh, seed.sh, audit.sh). Treat
# this file as the public API; refactor the implementation freely.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

_find_root() {
  local d="${1:-$PWD}"
  while [ "$d" != "/" ]; do
    [ -d "$d/agents/memory" ] && [ -f "$d/agents/memory/runtime/config/config.yaml" ] && [ -f "$d/agents/memory/scripts/memory.sh" ] && { echo "$d"; return 0; }
    d="$(dirname "$d")"
  done
  return 1
}

# Locate project root and cd to memory/ so neo4j-cli can read .env.
# Individual subcommands (node, rel, seed, audit) cd themselves; this
# default keeps `memory.sh query "<cypher>"` working from any cwd.
if root="$(_find_root)"; then
  cd "$root/agents/memory/runtime"
else
  echo "memory.sh: cannot find project root (no agents/memory/runtime/config/config.yaml or agents/memory/scripts/memory.sh)" >&2
  exit 2
fi

usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
}

sub="${1:-}"
[ -n "$sub" ] || { usage; exit 2; }
shift || true

case "$sub" in
  schema)
    case "${1:-}" in
      describe) shift; exec "$HERE/schema.sh" describe "$@" ;;
      validate) shift; exec "$HERE/schema.sh" validate "$@" ;;
      all)      exec "$HERE/schema.sh" all ;;
      ""|labels) exec "$HERE/schema.sh" labels ;;
      *) echo "memory.sh schema: unknown subcommand '$1'" >&2; exit 2 ;;
    esac
    ;;

  node)
    exec "$HERE/add-node.sh" "$@"
    ;;

  rel)
    exec "$HERE/add-rel.sh" "$@"
    ;;

  query)
    cypher="${1:?usage: memory.sh query \"<cypher>\"}"
    shift
    # Decide read vs write: if the user passed --rw, write; otherwise read.
    rw=0
    args=()
    for a in "$@"; do
      if [ "$a" = "--rw" ]; then rw=1; else args+=("$a"); fi
    done
    # ${args[@]+...} expands to nothing if the array is empty (set -u safe).
    if [ "$rw" = "1" ]; then
      exec neo4j-cli query "$cypher" --rw --format toon ${args[@]+"${args[@]}"}
    else
      exec neo4j-cli query "$cypher" --format toon ${args[@]+"${args[@]}"}
    fi
    ;;

  seed)
    exec "$HERE/seed.sh" "$@"
    ;;

  bootstrap-apply)
    exec "$HERE/bootstrap-apply.sh" "$@"
    ;;

  audit)
    exec "$HERE/audit.sh"
    ;;

  status)
    echo "--- docker ---"
    if root="$(_find_root)"; then
      ( cd "$root/agents/memory/runtime" && docker compose ps 2>&1 ) || echo "docker compose: not available"
    else
      echo "project root not found"
    fi
    echo
    echo "--- neo4j-cli ---"
    if command -v neo4j-cli >/dev/null 2>&1; then
      if root="$(_find_root)"; then
        ( cd "$root/agents/memory/runtime" && neo4j-cli query 'RETURN 1 AS ok' --format toon 2>&1 ) || echo "neo4j-cli: query failed"
      else
        echo "project root not found, cannot pick up memory/.env"
      fi
    else
      echo "neo4j-cli: not installed (expected at ~/.local/bin/neo4j-cli)"
    fi
    echo
    echo "--- graphiti mcp ---"
    curl -sS --max-time 5 http://localhost:8000/health 2>/dev/null || echo "graphiti-mcp: not reachable on :8000"
    ;;

  -h|--help|help)
    usage
    ;;

  *)
    echo "memory.sh: unknown subcommand '$sub'" >&2
    usage
    exit 2
    ;;
esac
