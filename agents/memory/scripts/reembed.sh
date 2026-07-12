#!/usr/bin/env bash
# agents/memory/scripts/reembed.sh
# Re-embebe el name+summary de cada nodo del proyecto (uno a uno) y
# actualiza la propiedad n.name_embedding. Idempotente: corre una vez
# para llegar al estado consistente.
#
# Usage:
#   reembed.sh                  # re-embebe los 87 nodos
#
# Estrategia: en lugar de re-corner todo el script de wrapper, hace un
# loop con un Cypher parametrizado que toma el embedding calculado
# localmente con embed.py y lo aplica al nodo. Es ~200ms por nodo, así
# que los 87 tardan ~20s.

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

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

# --- Project name (group_id) ---
GROUP_ID="$(cat "$ROOT/agents/memory/.project")"

# --- Extract all uuids + name + summary from the graph ---
# We use a sentinel "|||" (3 pipes) as the field separator and escape any
# newlines in the summary with "\n" so each record is exactly one line.
TMPFILE="$(mktemp -t reembed.XXXXXX)"
trap 'rm -f "$TMPFILE"' EXIT

neo4j-cli query "MATCH (n:Entity) WHERE n.group_id = '$GROUP_ID' RETURN n.uuid AS uuid, n.name AS name, coalesce(n.summary, '') AS summary" --max-rows 0 --format json 2>/dev/null \
  | python3 "$HERE/extract_nodes.py" > "$TMPFILE"

ROWS=()
while IFS= read -r line; do
  ROWS+=("$line")
done < "$TMPFILE"

# --- Re-derive summary field: convert literal "\n" back to real newlines
# for use in the embed text (the model understands real newlines). ---
decode_summary() {
  printf '%b' "$1"
}

total="${#ROWS[@]}"
ok=0
fail=0
i=0
echo "Re-embedding $total nodes..."
for row in "${ROWS[@]}"; do
  i=$((i+1))
  # Split by the "|||" sentinel (3 pipes). We use bash parameter expansion
  # instead of cut because cut can choke on multi-char delimiters in some
  # shells. The triple-pipe is unlikely to appear in node content.
  uuid="${row%%|||*}"
  rest="${row#*|||}"
  name="${rest%%|||*}"
  summary_encoded="${rest#*|||}"
  summary="$(decode_summary "$summary_encoded")"
  emb_text="${name} — ${summary}"
  emb_json="$("$HERE/embed.py" "$emb_text" 2>/dev/null || true)"
  if [ -z "$emb_json" ] || [ "${emb_json:0:1}" != "[" ]; then
    echo "  [$i/$total] FAIL: $uuid ($name)"
    fail=$((fail+1))
    continue
  fi
  # Apply embedding
  if neo4j-cli query "MATCH (n:Entity {uuid: \$uuid, group_id: \$gid}) SET n.name_embedding = \$emb RETURN n.uuid AS uuid" --param "uuid=$uuid" --param "gid=$GROUP_ID" --param "emb=$emb_json" --rw --format toon >/dev/null 2>&1; then
    ok=$((ok+1))
  else
    echo "  [$i/$total] FAIL: $uuid ($name)"
    fail=$((fail+1))
  fi
  # progress every 10
  if [ $((i % 10)) -eq 0 ]; then
    echo "  ... $i/$total done (ok=$ok fail=$fail)"
  fi
done

echo
echo "--- reembed summary ---"
echo "total: $total"
echo "ok:    $ok"
echo "fail:  $fail"
