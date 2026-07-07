#!/usr/bin/env bash
# Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.

# agents/memory/scripts/add-rel.sh
# Validates that src and dst exist, then runs a MERGE that creates or
# updates a typed relation. Idempotent.
#
# Usage:
#   add-rel.sh --type <REL_TYPE> --src <uuid> --dst <uuid> [--group-id <gid>] [--prop k=v ...]
#
# Example:
#   add-rel.sh --type TESTS --src inv-foo --dst inv-bar
#   add-rel.sh --type INCLUDES --src inv-foo --dst paper-x --prop role=anchor
#
# Project name (group_id) is resolved via lib/project.sh:
#   --group-id <gid> > $GROUP_ID env > agents/memory/.project

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/project.sh
source "$HERE/lib/project.sh"

_find_root() {
  local d="${1:-$PWD}"
  while [ "$d" != "/" ]; do
    [ -d "$d/agents/memory" ] && [ -f "$d/agents/memory/runtime/config/config.yaml" ] && [ -f "$d/agents/memory/scripts/memory.sh" ] && { echo "$d"; return 0; }
    d="$(dirname "$d")"
  done
  return 1
}
ROOT="$(_find_root)"
cd "$ROOT/agents/memory/runtime"

# --- defaults ---
type=""
src=""
dst=""
group_id=""
prop_names=()
prop_values=()

# --- parse flags ---
while [ $# -gt 0 ]; do
  case "$1" in
    --type)      type="${2:-}"; shift 2 ;;
    --src)       src="${2:-}"; shift 2 ;;
    --dst)       dst="${2:-}"; shift 2 ;;
    --group-id)  group_id="${2:-}"; shift 2 ;;
    --prop)
      kv="${2:-}"
      k="${kv%%=*}"
      v="${kv#*=}"
      if [ -z "$k" ] || [ "$k" = "$kv" ]; then
        echo "add-rel.sh: --prop expects key=value, got '$kv'" >&2
        exit 2
      fi
      prop_names+=("$k")
      prop_values+=("$v")
      shift 2
      ;;
    -h|--help)
      sed -n '2,17p' "$0"; exit 0 ;;
    *)
      echo "add-rel.sh: unknown flag '$1'" >&2
      exit 2 ;;
  esac
done

for v in type src dst; do
  if [ -z "${!v}" ]; then
    echo "add-rel.sh: --$v is required" >&2
    exit 2
  fi
done

# --- resolve project (group_id) ---
resolve_project "$group_id" || exit 2
group_id="$GROUP_ID"

# --- build the SET clause for extra properties (if any) ---
set_clause="r.group_id = \$gid, r.created_at = datetime()"
for i in "${!prop_names[@]}"; do
  k="${prop_names[$i]}"
  # Escape backticks in property name; reject spaces.
  if [[ "$k" =~ [[:space:]\`\'\"\\] ]]; then
    echo "add-rel.sh: invalid property name '$k'" >&2
    exit 2
  fi
  set_clause="${set_clause}, r.${k} = \$prop_${i}"
done

# --- build Cypher with a guard MATCH so we fail loudly if src/dst missing ---
# We do this in two steps: (1) ensure both endpoints exist; (2) MERGE the rel.
# If either endpoint is missing, exit 2 (the user gave us bad uuids).

check_cypher=$(cat <<EOF
MATCH (a:Entity {uuid: \$src, group_id: \$gid})
MATCH (b:Entity {uuid: \$dst, group_id: \$gid})
RETURN a.uuid AS src_ok, b.uuid AS dst_ok
EOF
)

check_params=("--param" "src=$src" "--param" "dst=$dst" "--param" "gid=$group_id")
check_out="$(neo4j-cli query "$check_cypher" "${check_params[@]}" --format toon 2>&1)"

if echo "$check_out" | grep -q "src_ok" && echo "$check_out" | grep -q "dst_ok" \
   && ! echo "$check_out" | grep -qE "rows:#\s*0\b"; then
  :
else
  echo "add-rel.sh: src='$src' and/or dst='$dst' (group_id='$group_id') do not exist" >&2
  exit 2
fi

# --- the MERGE itself ---
merge_cypher=$(cat <<EOF
MATCH (a:Entity {uuid: \$src, group_id: \$gid})
MATCH (b:Entity {uuid: \$dst, group_id: \$gid})
MERGE (a)-[r:${type}]->(b)
  ON CREATE SET ${set_clause}
  ON MATCH  SET ${set_clause}
RETURN type(r) AS rel, r.group_id AS gid
EOF
)

params=("--param" "src=$src" "--param" "dst=$dst" "--param" "gid=$group_id")
for i in "${!prop_names[@]}"; do
  params+=("--param" "prop_${i}=${prop_values[$i]}")
done

neo4j-cli query "$merge_cypher" "${params[@]}" --rw --format toon

# --- log ---
mkdir -p "$ROOT/runs"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  "add-rel" \
  "$group_id" \
  "$type" \
  "$src" \
  "$dst" \
  "$(IFS=,; echo "${prop_names[*]:-}")" \
  >> "$ROOT/runs/memory.log"
