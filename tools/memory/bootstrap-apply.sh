#!/usr/bin/env bash
# PROTECTED: requires user approval to edit (see opencode.json permission.edit).
#
# tools/memory/bootstrap-apply.sh
# Reads every *.yaml in tools/memory/bootstrap/ and applies it as ONE
# atomic write. Idempotent: every MERGE keys on uuid + group_id, so
# re-running converges.
#
# This is the "pre-configured knowledge" mechanism: drop a yaml in
# tools/memory/bootstrap/ and the next invocation of this script (or
# `make bootstrap-apply`, or `make session-start`) will add it to the
# graph. Use it for entries that should be present in every session —
# project-level architecture, conventions, modules, the agents layer.
# It is NOT for one-shot project init (that's seed.sh / make seed).
#
# Why a folder and not a single file:
#   - Per-entry review (small diffs, easy to revert one file).
#   - Filename prefix gives a stable order (00-, 01-, 02-).
#   - Multiple authors can each own one file.
#   - The single `seed/<project>.yaml` stays focused on the initial
#     project bootstrap (modules, datasets, top-level investigation).
#
# Usage:
#   bootstrap-apply.sh <group_id> [--dry-run]
#
# Exit codes:
#   0  ok (atomic write succeeded or dry-run printed)
#   1  schema / parsing / write failure
#   2  usage

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

_find_root() {
  local d="${1:-$PWD}"
  while [ "$d" != "/" ]; do
    [ -d "$d/memory" ] && [ -f "$d/memory/config/config.yaml" ] && { echo "$d"; return 0; }
    d="$(dirname "$d")"
  done
  return 1
}

usage() {
  sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
}

group_id="${1:-}"
shift || true
dry_run=0
[ "${1:-}" = "--dry-run" ] && dry_run=1

if [ -z "$group_id" ]; then
  usage
  exit 2
fi

if ! ROOT="$(_find_root)"; then
  echo "bootstrap-apply.sh: cannot find project root (no memory/config/config.yaml)" >&2
  exit 2
fi

BOOTSTRAP_DIR="$HERE/../bootstrap"
# Resolve absolute so it works regardless of cwd.
BOOTSTRAP_DIR="$(cd "$BOOTSTRAP_DIR" 2>/dev/null && pwd)" || {
  echo "bootstrap-apply.sh: missing bootstrap directory at $HERE/../bootstrap" >&2
  exit 2
}

# Find yamls (sorted by name, so 00- comes before 01-).
shopt -s nullglob
YAMLS=( "$BOOTSTRAP_DIR"/*.yaml )
shopt -u nullglob

if [ "${#YAMLS[@]}" -eq 0 ]; then
  echo "bootstrap-apply.sh: no .yaml files in $BOOTSTRAP_DIR (nothing to apply)"
  exit 0
fi

# --- parse every yaml into a per-file tmp dir, then merge into one ---
RUN="$(mktemp -d -t bootstrap-XXXXXX)"
trap 'rm -rf "$RUN"' EXIT
MERGED="$RUN/merged"
mkdir -p "$MERGED"

for yaml in "${YAMLS[@]}"; do
  python3 "$HERE/lib/parse-yaml.py" "$yaml" "$RUN/$(basename "$yaml" .yaml)"
done

# Concatenate every per-file section into one merged file.
merge_section() {
  local section="$1"
  : > "$MERGED/$section"
  for d in "$RUN"/*/; do
    [ -f "$d/$section" ] || continue
    cat "$d/$section" >> "$MERGED/$section"
  done
}

for s in components investigations pitfalls preferences architectures tools patterns operational relations; do
  merge_section "$s"
done

# --- validate every label is in the schema before any write ---
for label in Component Investigation Architecture Pattern Pitfall Tool Operational Preference; do
  if ! "$HERE/schema.sh" validate "$label" >/dev/null 2>&1; then
    echo "bootstrap-apply.sh: schema does not contain label '$label'" >&2
    exit 1
  fi
done

# --- build the Cypher ---
cypher="$(mktemp -t bootstrap-XXXXXX.cypher)"
trap 'rm -rf "$RUN"; rm -f "$cypher"' EXIT

emit_nodes() {
  local label="$1" section_file="$2"
  [ -s "$section_file" ] || return 0
  local i=0
  while IFS=$'\t' read -r uuid name summary rest; do
    [ -z "$uuid" ] && continue
    if [ -z "$name" ]; then
      echo "bootstrap-apply.sh: $label section has entry without 'name' (uuid=$uuid)" >&2
      exit 2
    fi
    local status="" path=""
    if [ "$label" = "Investigation" ]; then
      status="$rest"
      read -r path <<< ""
    else
      path="$rest"
    fi
    local prefix="${label}_${i}"
    {
      echo "MERGE (n:Entity:${label} {uuid: \$${prefix}_uuid, group_id: \$gid})"
      echo "  ON CREATE SET n.name = \$${prefix}_name,"
      echo "                n.summary = \$${prefix}_summary,"
      echo "                n.path = \$${prefix}_path,"
      [ -n "$status" ] && echo "                n.status = \$${prefix}_status,"
      echo "                n.created_at = datetime()"
      echo "  ON MATCH  SET n.name = \$${prefix}_name,"
      echo "                n.summary = \$${prefix}_summary,"
      echo "                n.path = \$${prefix}_path,"
      [ -n "$status" ] && echo "                n.status = \$${prefix}_status,"
      echo "                n.updated_at = datetime();"
    } >> "$cypher"
    params+=("--param" "${prefix}_uuid=$uuid")
    params+=("--param" "${prefix}_name=$name")
    params+=("--param" "${prefix}_summary=${summary:-}")
    params+=("--param" "${prefix}_path=${path:-}")
    [ -n "$status" ] && params+=("--param" "${prefix}_status=$status")
    i=$((i+1))
  done < "$section_file"
}

params=("--param" "gid=$group_id")

emit_nodes "Component"      "$MERGED/components"
emit_nodes "Investigation"  "$MERGED/investigations"
emit_nodes "Pitfall"        "$MERGED/pitfalls"
emit_nodes "Preference"     "$MERGED/preferences"
emit_nodes "Architecture"   "$MERGED/architectures"
emit_nodes "Tool"           "$MERGED/tools"
emit_nodes "Pattern"        "$MERGED/patterns"
emit_nodes "Operational"    "$MERGED/operational"

# --- relations ---
i=0
while IFS=$'\t' read -r src type dst props; do
  [ -z "$src" ] && continue
  if [ -z "$type" ] || [ -z "$dst" ]; then
    echo "bootstrap-apply.sh: relations[$i] missing src/type/dst" >&2
    exit 2
  fi
  set_clause="r.group_id = \$gid, r.created_at = datetime()"
  if [ -n "$props" ]; then
    IFS=',' read -ra kvs <<< "$props"
    for kv in "${kvs[@]}"; do
      k="${kv%%=*}"
      v="${kv#*=}"
      if [ -n "$k" ] && [ "$k" != "$kv" ]; then
        set_clause="${set_clause}, r.${k} = \$r_${i}_p_${k}"
        params+=("--param" "r_${i}_p_${k}=${v}")
      fi
    done
  fi
  {
    echo "MATCH (a:Entity {uuid: \$r_${i}_src, group_id: \$gid})"
    echo "MATCH (b:Entity {uuid: \$r_${i}_dst, group_id: \$gid})"
    echo "MERGE (a)-[r:${type}]->(b)"
    echo "  ON CREATE SET ${set_clause}"
    echo "  ON MATCH  SET ${set_clause};"
  } >> "$cypher"
  params+=("--param" "r_${i}_src=$src")
  params+=("--param" "r_${i}_dst=$dst")
  i=$((i+1))
done < "$MERGED/relations"

# --- dry-run? ---
if [ "$dry_run" = "1" ]; then
  cat "$cypher"
  echo
  echo "# params: ${#params[@]}"
  echo "# files: ${#YAMLS[@]} yaml(s) in $BOOTSTRAP_DIR"
  exit 0
fi

# --- log + execute ---
mkdir -p "$ROOT/runs"
{
  echo "# bootstrap-apply.sh $group_id $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "# files: ${#YAMLS[@]} yaml(s) in $BOOTSTRAP_DIR"
  echo "# nodes: $(grep -c '^MERGE (n:Entity:' "$cypher" || echo 0)"
  echo "# rels:  $(grep -c '^MERGE (a)-\[r:' "$cypher" || echo 0)"
  cat "$cypher"
} >> "$ROOT/runs/memory.log"

# Run from the memory/ dir so neo4j-cli picks up the .env.
(
  cd "$ROOT/memory" && \
  neo4j-cli query "$(cat "$cypher")" --rw --atomic --format toon "${params[@]}"
)

echo "bootstrap-apply.sh: applied ${#YAMLS[@]} file(s) to group_id=$group_id (idempotent on uuid+group_id)"
