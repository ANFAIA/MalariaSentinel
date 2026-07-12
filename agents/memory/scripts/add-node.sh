#!/usr/bin/env bash
# Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.

# agents/memory/scripts/add-node.sh
# Validates a label against the schema, then runs a MERGE that creates or
# updates a typed node. Idempotent: re-running with the same uuid is a no-op
# except for property updates.
#
# Usage:
#   add-node.sh --type <Label> --uuid <id> --name <n> --summary <s> \
#               [--path <p>] [--parent <uuid>] [--group-id <gid>]
#
# The label is validated against agents/memory/scripts/schema.sh. If invalid, exits 1
# without writing. The script always uses --rw (it is a write).
#
# If --parent is passed, a (parent)-[:PART_OF]-(child) edge is created in the
# same Cypher. The parent must exist or the write fails.
#
# Project name (group_id) is resolved via lib/project.sh:
#   --group-id <gid> > $GROUP_ID env > agents/memory/.project

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
parent=""

# --- parse flags ---
while [ $# -gt 0 ]; do
  case "$1" in
    --type)    type="${2:-}"; shift 2 ;;
    --uuid)    uuid="${2:-}"; shift 2 ;;
    --name)    name="${2:-}"; shift 2 ;;
    --summary) summary="${2:-}"; shift 2 ;;
    --path)    path="${2:-}"; shift 2 ;;
    --parent)  parent="${2:-}"; shift 2 ;;
    --group-id) group_id="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '2,18p' "$0"; exit 0 ;;
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

# --- Embedding: call embed.py to get a 1536-dim vector for the
# concatenation of name + summary. If embed.py fails (OpenAI down, no key),
# we log a warning and skip the embedding — the node is still created
# (degraded mode: the node is valid but won't be findable by memory_recall
# until reembedded). ---
emb_text="${name} — ${summary}"
emb_json="$("$HERE/embed.py" "$emb_text" 2>/dev/null || true)"
if [ -n "$emb_json" ] && [ "${emb_json:0:1}" = "[" ]; then
  params+=("--param" "embedding=$emb_json")
  HAS_EMBEDDING=1
else
  echo "add-node.sh: WARNING: embedding skipped (embed.py failed). Node will be invisible to memory_recall until reembedded." >&2
  HAS_EMBEDDING=0
fi

# --- the actual Cypher. We MERGE on (uuid, group_id) so a second run with
# the same uuid updates the visible properties without changing the
# identity. The schema label is set via SET (not in the MERGE pattern)
# so an existing Entity-only node can be "promoted" to the right schema
# label by a subsequent memory_node call — the previous version had the
# label inside the MERGE pattern (:Entity:${type}) which forced a fresh
# node to be created when the existing one didn't yet carry the label,
# producing duplicate nodes on promotion. ---
if [ -n "$parent" ]; then
  # With parent: the (parent)-[:PART_OF]->(child) edge is created in the
  # same transaction. We use MATCH (not MERGE) for the parent so the
  # write fails loudly if the parent does not exist (no silent-orphan
  # creation — better to fail than to have a child with a fake parent).
  if [ "$HAS_EMBEDDING" = "1" ]; then
    cypher="MATCH (parent:Entity {uuid: \$parent_uuid, group_id: \$gid})
  WITH parent
  MERGE (n:Entity {uuid: \$uuid, group_id: \$gid})
    ON CREATE SET n:${type},
                  n.name = \$name,
                  n.summary = \$summary,
                  n.path = \$path,
                  n.name_embedding = \$embedding,
                  n.created_at = datetime()
    ON MATCH  SET n:${type},
                  n.name = \$name,
                  n.summary = \$summary,
                  n.path = \$path,
                  n.name_embedding = \$embedding
  WITH parent, n
  MERGE (n)-[r:PART_OF {group_id: \$gid}]->(parent)
    ON CREATE SET r.created_at = datetime()
  RETURN n.uuid AS uuid, labels(n) AS labels"
  else
    cypher="MATCH (parent:Entity {uuid: \$parent_uuid, group_id: \$gid})
  WITH parent
  MERGE (n:Entity {uuid: \$uuid, group_id: \$gid})
    ON CREATE SET n:${type},
                  n.name = \$name,
                  n.summary = \$summary,
                  n.path = \$path,
                  n.created_at = datetime()
    ON MATCH  SET n:${type},
                  n.name = \$name,
                  n.summary = \$summary,
                  n.path = \$path
  WITH parent, n
  MERGE (n)-[r:PART_OF {group_id: \$gid}]->(parent)
    ON CREATE SET r.created_at = datetime()
  RETURN n.uuid AS uuid, labels(n) AS labels"
  fi
  params+=("--param" "parent_uuid=$parent")
else
  if [ "$HAS_EMBEDDING" = "1" ]; then
    cypher="MERGE (n:Entity {uuid: \$uuid, group_id: \$gid})
    ON CREATE SET n:${type},
                  n.name = \$name,
                  n.summary = \$summary,
                  n.path = \$path,
                  n.name_embedding = \$embedding,
                  n.created_at = datetime()
    ON MATCH  SET n:${type},
                  n.name = \$name,
                  n.summary = \$summary,
                  n.path = \$path,
                  n.name_embedding = \$embedding
  RETURN n.uuid AS uuid, labels(n) AS labels"
  else
    cypher="MERGE (n:Entity {uuid: \$uuid, group_id: \$gid})
    ON CREATE SET n:${type},
                  n.name = \$name,
                  n.summary = \$summary,
                  n.path = \$path,
                  n.created_at = datetime()
    ON MATCH  SET n:${type},
                  n.name = \$name,
                  n.summary = \$summary,
                  n.path = \$path
  RETURN n.uuid AS uuid, labels(n) AS labels"
  fi
fi

# --- find the project root, then run from memory/ so neo4j-cli finds .env ---
_find_root() {
  local d="${1:-$PWD}"
  while [ "$d" != "/" ]; do
    [ -d "$d/agents/memory" ] && [ -f "$d/agents/memory/runtime/config/config.yaml" ] && [ -f "$d/agents/memory/scripts/memory.sh" ] && { echo "$d"; return 0; }
    d="$(dirname "$d")"
  done
  return 1
}
ROOT="$(_find_root)"

(
  cd "$ROOT/agents/memory/runtime" && \
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
