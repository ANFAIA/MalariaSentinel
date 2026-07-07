#!/usr/bin/env bash
# Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.

# agents/memory/scripts/session-end.sh
# Prints the session-end checklist. The agent reads it, follows it, and
# writes a session summary. The narrative goes in a free-form episode;
# the structure goes in typed node updates.
#
# Usage:
#   session-end.sh
#
# This script does NOT make any writes. It is a printable checklist.

cat <<'EOF'
=== session-end checklist ===

Before you stop, do the following in order:

1. UPDATE Investigations
   For every Investigation node you worked on:
     bash tools/memory/memory.sh node \
       --type Investigation --uuid <inv-uuid> \
       --name "<name>" \
       --summary "Goal: ... Method: ... Findings: ... Status: open|blocked|closed"
   The "Status:" line is the last line so the session-start query can
   filter on it.

2. ADD any new Components, Tools, Patterns, Pitfalls, Architecture, or
   Operational nodes you discovered:
     bash tools/memory/memory.sh node --type <L> --uuid <id> --name <n> --summary <s>
     bash tools/memory/memory.sh rel --type <R> --src <a> --dst <b>

3. WRITE a session episode (one per session, not per day):
   mcp__graphiti-memory__add_memory \
     --name "session-YYYY-MM-DD: <topic>" \
     --episode_body "What I did: ... Decisions: ... Blockers: ... Next: ..." \
     --source message --source_description "agent"

4. EDIT AGENTS.md if you introduced a new convention. The next agent
   reads it cold; the graph complements, doesn't replace it.

5. RUN `make audit` to confirm the graph is still clean after your writes.

=== done ===
EOF
