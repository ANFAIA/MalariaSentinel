#!/usr/bin/env bash
# agents/memory/scripts/recall.sh
# Semantic recall over the project knowledge graph. Embeds the query,
# runs a vector search against the entity_name_embedding index, then for
# each hit attaches (a) the chain to the root through PART_OF edges, and
# (b) the depth-1 neighbourhood (any verb, both directions).
#
# Usage:
#   recall.sh <query> [k] [depth] [gid]
#     query: natural-language query
#     k:     top-k hits (default 5)
#     depth: neighbourhood depth (default 1)
#     gid:   group_id (default: read from agents/memory/.project)
#
# Output: a JSON object with the shape:
#   { "hits": [
#       {
#         "node":   { "uuid", "name", "summary", "labels" },
#         "score":  <float>,
#         "chain_to_root": [ "<uuid>", ... ],
#         "connected": [
#           { "rel": "PART_OF", "dir": "in"|"out",
#             "node": { "uuid", "name", "summary" } },
#           ...
#         ]
#       },
#       ...
#     ]
#   }

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

query="${1:-}"
k="${2:-5}"
depth="${3:-1}"
gid_arg="${4:-}"

if [ -z "$query" ]; then
  echo '{"error": "recall.sh: query is required"}' >&2
  exit 2
fi

# --- find project root + resolve group_id ---
_find_root() {
  local d="${1:-$HERE}"
  while [ "$d" != "/" ]; do
    [ -d "$d/agents/memory" ] && [ -f "$d/agents/memory/runtime/config/config.yaml" ] && [ -f "$d/agents/memory/scripts/memory.sh" ] && { echo "$d"; return 0; }
    d="$(dirname "$d")"
  done
  return 1
}
ROOT="$(_find_root)"
if [ -n "$gid_arg" ]; then
  GROUP_ID="$gid_arg"
else
  GROUP_ID="$(cat "$ROOT/agents/memory/.project")"
fi

# --- embed the query ---
emb_json="$("$HERE/embed.py" "$query" 2>/dev/null || true)"
if [ -z "$emb_json" ] || [ "${emb_json:0:1}" != "[" ]; then
  echo '{"error": "recall.sh: embed.py failed (OpenAI unreachable or no key)"}' >&2
  exit 1
fi

# --- run the recall query ---
# We use a single Cypher that:
#  1. runs vector query to get top-k hits
#  2. for each hit, OPTIONAL MATCH (hit)-[r]-(m) where depth <= $depth
#  3. for each hit, OPTIONAL MATCH path = (root)-[:PART_OF*]->(hit) for the chain
# Returns raw rows that we post-process in Python (Cypher can't easily
# produce nested JSON for variable-length paths).
cd "$ROOT/agents/memory/runtime"

cypher="CALL db.index.vector.queryNodes('entity_name_embedding', ${k}, \$q) YIELD node, score
WITH node, score
ORDER BY score DESC
LIMIT ${k}
WITH collect({node: node, score: score}) AS hits
UNWIND hits AS h
WITH h.node AS n, h.score AS score
// chain_to_root: PART_OF goes child -> parent, so we walk (n)-[:PART_OF*]->(root).
// The chain is returned in child-first order (n, parent, grandparent, ...).
OPTIONAL MATCH path = (n)-[:PART_OF*..6]->(root)
  WHERE root.group_id = \$gid
    AND all(rel IN relationships(path) WHERE rel.group_id = \$gid)
WITH n, score,
     [x IN nodes(path) | x.uuid] AS chain
// connected: all depth-1 neighbors, both directions, any verb except PART_OF
// (PART_OF is already in chain_to_root; the user wants lateral edges here).
OPTIONAL MATCH (n)-[r]-(m)
  WHERE r.group_id = \$gid AND m.group_id = \$gid AND type(r) <> 'PART_OF'
WITH n, score, chain,
     collect({rel: type(r), dir: CASE WHEN startNode(r) = n THEN 'out' ELSE 'in' END, uuid: m.uuid, name: m.name, summary: m.summary}) AS connected
RETURN n.uuid AS uuid, labels(n) AS labels, n.name AS name, n.summary AS summary, score, chain, connected
ORDER BY score DESC"

tmp_cypher_out="$(mktemp -t recall.XXXXXX)"
trap 'rm -f "$tmp_cypher_out"' EXIT

neo4j-cli query "$cypher" \
  --param "q=$emb_json" \
  --param "gid=$GROUP_ID" \
  --max-rows 0 \
  --truncate-arrays-over 0 \
  --format json > "$tmp_cypher_out" 2>/dev/null

# --- Fail loud if the query returned nothing usable. The vector search
# itself should always return a valid result; if it didn't, something is
# wrong (empty embedding, bad group_id, missing index, etc.). ---
if [ ! -s "$tmp_cypher_out" ]; then
  echo '{"error": "recall.sh: neo4j-cli returned no output", "k": '"$k"', "gid": "'"$GROUP_ID"'", "embedding_len": '"${#emb_json}"'}' >&2
  exit 1
fi

# --- post-process with python to assemble the final JSON shape ---
python3 "$HERE/recall_postprocess.py" "$tmp_cypher_out" "$k"
