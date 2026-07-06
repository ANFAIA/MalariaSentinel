#!/usr/bin/env bash
# PROTECTED: requires human-in-the-loop approval to edit.
# See tools/memory/.protected and AGENTS.md (Protected files).

# tools/memory/add-node.sh
# Validates a label against the schema, then runs a MERGE that creates or
# updates a typed node. Idempotent: re-running with the same uuid is a no-op
# except for property updates.
#
# Usage:
#   add-node.sh --type <Label> --uuid <id> --name <n> --summary <s> [--path <p>] [--group-id <gid>]
#
# The label is validated against tools/memory/schema.sh. If invalid, exits 1
# without writing. The script always uses --rw (it is a write).
#
# Project name (group_id) is resolved via lib/project.sh:
#   --group-id <gid> > $GROUP_ID env > tools/memory/.project

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/project.sh
source "$HERE/lib/project.sh"

# --- defaults ---
type=""
uuid=""
name=""
summary=""
path=""
group_id=""

# --- parse flags ---
while [ $# -gt 0 ]; do
  case "$1" in
    --type)    type="${2:-}"; shift 2 ;;
    --uuid)    uuid="${2:-}"; shift 2 ;;
    --name)    name="${2:-}"; shift 2 ;;
    --summary) summary="${2:-}"; shift 2 ;;
    --path)    path="${2:-}"; shift 2 ;;
    --group-id) group_id="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '2,16p' "$0"; exit 0 ;;
    *)
      echo "add-node.sh: unknown flag '$1'" >&2
      exit 2 ;;
  esac
done

# --- validate required ---
for v in type uuid name summary; do
  if [ -z "${!v}" ]; then
    echo "add-node.sh: --$v is required" >&2
    exit 2
  fi
done

# --- resolve project (group_id) ---
resolve_project "$group_id" || exit 2
group_id="$GROUP_ID"

# --- validate label against schema ---
if ! "$HERE/schema.sh" validate "$type" >/dev/null 2>&1; then
  "$HERE/schema.sh" validate "$type" || true
  exit 1
fi

# --- escape single quotes for the Cypher literal (we use parameterised
# values via --param, so this is just for the file system / log path).
# Actually we use --param to keep everything safe. Build the params. ---
# We still need a path-string to bind. Empty path -> empty string.
# neo4j-cli --param syntax: NAME:value  (string). For an empty value we
# pass an explicit empty token by using "" inline.

params=(
  "--param" "uuid=$uuid"
  "--param" "gid=$group_id"
  "--param" "name=$name"
  "--param" "summary=$summary"
  "--param" "path=$path"
)

# --- the actual Cypher. We MERGE on (uuid, group_id) so a second run with
# the same uuid updates the visible properties without changing the
# identity. ---
cypher="MERGE (n:Entity:${type} {uuid: \$uuid, group_id: \$gid})
  ON CREATE SET n.name = \$name,
                n.summary = \$summary,
                n.path = \$path,
                n.created_at = datetime()
  ON MATCH  SET n.name = \$name,
                n.summary = \$summary,
                n.path = \$path
RETURN n.uuid AS uuid, labels(n) AS labels"

# --- find the project root, then run from memory/ so neo4j-cli finds .env ---
_find_root() {
  local d="${1:-$PWD}"
  while [ "$d" != "/" ]; do
    [ -d "$d/memory" ] && [ -f "$d/memory/config/config.yaml" ] && { echo "$d"; return 0; }
    d="$(dirname "$d")"
  done
  return 1
}
ROOT="$(_find_root)"

(
  cd "$ROOT/memory" && \
  neo4j-cli query "$cypher" "${params[@]}" --rw --format toon
)

# --- log the write ---
mkdir -p "$ROOT/runs"
printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  "add-node" \
  "$group_id" \
  "$type" \
  "$uuid" \
  "$name" \
  >> "$ROOT/runs/memory.log"
