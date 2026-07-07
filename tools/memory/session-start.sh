#!/usr/bin/env bash
# PROTECTED: requires human-in-the-loop approval to edit.
# See tools/memory/.protected and AGENTS.md (Protected files).

# tools/memory/session-start.sh
# The session-start routine. Run at the start of every session that
# touches the project. The agent should glance at the output, then know
# what state the project is in before they do anything.
#
# Usage:
#   session-start.sh <group_id>
#
# The script is project-agnostic — the Makefile passes the resolved slug.
# It runs:
#   0. apply pre-configured bootstrap entries (tools/memory/bootstrap/*.yaml)
#   1. audit (fail fast on drift)
#   2. open investigations
#   3. active pitfalls (must-read)
#   4. architecture decisions in force
#   5. component map (one row per Component)
#   6. preferences (user-stated, treat as immutable)
#   7. operational patterns
#   8. recent free-form episodes (last 14 days, via MCP search_nodes)

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
GID="${1:?usage: session-start.sh <group_id>}"

echo "=== session-start: $GID ==="
echo

# 0. apply pre-configured bootstrap entries (idempotent; safe every session)
echo "--- 0. apply bootstrap entries (tools/memory/bootstrap/) ---"
bash "$HERE/bootstrap-apply.sh" "$GID" || { echo "BOOTSTRAP APPLY FAILED — fix the offending yaml and re-run."; exit 1; }
echo

# 1. audit
echo "--- 1. audit (drift check) ---"
bash "$HERE/audit.sh" || { echo "AUDIT FAILED — read Self-correction in AGENTS.md before continuing."; exit 1; }
echo

_q() {
  local title="$1"; local cypher="$2"
  echo "--- $title ---"
  bash "$HERE/memory.sh" query "$cypher" 2>&1
  echo
}

# 2. open investigations
# An Investigation is "open" if:
#   - i.status field is null/missing or anything other than 'closed', AND
#   - the summary does NOT end with "Status: closed"
# This way the convention "Status: open|blocked|closed is the last line
# of summary" is respected without requiring a typed `status` field.
_q "2. open investigations" \
  "MATCH (i:Investigation) WHERE i.group_id = '$GID' AND (i.status IS NULL OR i.status <> 'closed') AND NOT coalesce(i.summary, '') CONTAINS 'Status: closed' RETURN i.uuid AS uuid, i.name AS name, i.summary AS summary ORDER BY i.created_at"

# 3. active pitfalls
_q "3. active pitfalls (must-read)" \
  "MATCH (p:Pitfall) WHERE p.group_id = '$GID' RETURN p.uuid AS uuid, p.name AS name, p.summary AS summary ORDER BY p.created_at"

# 4. architecture decisions in force
_q "4. architecture decisions" \
  "MATCH (a:Architecture) WHERE a.group_id = '$GID' RETURN a.uuid AS uuid, a.name AS name, a.summary AS summary ORDER BY a.created_at"

# 5. component map
_q "5. component map" \
  "MATCH (c:Component) WHERE c.group_id = '$GID' RETURN c.uuid AS uuid, c.name AS name, c.path AS path ORDER BY c.name"

# 6. preferences (user-stated values, treat as immutable)
_q "6. preferences" \
  "MATCH (p:Preference) WHERE p.group_id = '$GID' RETURN p.uuid AS uuid, p.name AS name, p.summary AS summary"

# 7. operational patterns
_q "7. operational patterns" \
  "MATCH (o:Operational) WHERE o.group_id = '$GID' RETURN o.uuid AS uuid, o.name AS name, o.summary AS summary"

# 8. recent free-form episodes (only works if MCP is reachable)
echo "--- 8. recent free-form episodes (last 14 days) ---"
if command -v curl >/dev/null && curl -sS --max-time 3 http://localhost:8000/health >/dev/null 2>&1; then
  echo "(call mcp__graphiti-memory__search_nodes --query 'session' to retrieve)"
else
  echo "(graphiti-mcp not reachable on :8000; skipping)"
fi
echo

echo "=== session-start: done ==="
echo "If you proceed, run \`make session-end\` before stopping."
