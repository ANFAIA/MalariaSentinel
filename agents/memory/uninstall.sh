#!/usr/bin/env bash
# agents/memory/uninstall.sh
# Best-effort reverser for install.sh. Removes the opencode-stubs that
# were copied, reverses the opencode.json patches and the .gitignore
# patches. Does NOT delete agents/memory/ itself — that's a manual
# `git rm -r` since the module is the project's source of truth.
#
# Usage:
#   bash agents/memory/uninstall.sh              # interactive confirm
#   bash agents/memory/uninstall.sh --yes        # skip confirm

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# The module is at <project_root>/agents/memory/, so the project root is
# two levels up from HERE.
PROJECT_ROOT="$(cd "$HERE/../.." && pwd)"

ASSUME_YES=0
while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes) ASSUME_YES=1; shift ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "uninstall.sh: unknown flag '$1'" >&2; exit 2 ;;
  esac
done

if [ "$ASSUME_YES" != "1" ]; then
  read -r -p "Remove agents/memory opencode-stubs and reverse opencode.json/.gitignore patches? [y/N] " ans < /dev/tty
  case "${ans:-N}" in y|Y|yes|YES) ;; *) echo "aborted."; exit 1 ;; esac
fi

# ---- 1. remove the skill ----
SKILL_DST_DIR="$PROJECT_ROOT/.agents/skills/project-memory"
if [ -d "$SKILL_DST_DIR" ]; then
  rm -rf "$SKILL_DST_DIR"
  echo "removed: $SKILL_DST_DIR"
else
  echo "skip (not found): $SKILL_DST_DIR"
fi

# ---- 2. remove the 6 custom tool files ----
TOOLS_DST_DIR="$PROJECT_ROOT/.opencode/tools"
removed_tools=0
for tool_name in memory_node memory_rel memory_query memory_audit memory_seed memory_status; do
  f="$TOOLS_DST_DIR/${tool_name}.ts"
  if [ -f "$f" ]; then
    rm -f "$f"
    echo "removed: $f"
    removed_tools=$((removed_tools + 1))
  fi
done
if [ "$removed_tools" = "0" ]; then
  echo "no custom tool files found in $TOOLS_DST_DIR"
fi

# ---- 3. reverse opencode.json patches (idempotent) ----
OPENCODE_JSON="$PROJECT_ROOT/opencode.json"
if [ ! -f "$OPENCODE_JSON" ]; then
  echo "skip (not found): $OPENCODE_JSON"
else
  command -v jq >/dev/null 2>&1 || { echo "uninstall.sh: 'jq' is required to patch opencode.json" >&2; exit 2; }

  tmp_json="$(mktemp -t uninstall-opencode-XXXXXX.json)"
  trap 'rm -f "$tmp_json"' EXIT
  cp "$OPENCODE_JSON" "$tmp_json"

  # Remove edit-protection for .project
  tmp_json="$(mktemp -t uninstall-opencode-XXXXXX.json)"
  jq 'del(.permission.edit["agents/memory/.project"])' \
    "$tmp_json" > "${tmp_json}.new" && mv "${tmp_json}.new" "$tmp_json"

  # Remove bash deny rules
  tmp_json="$(mktemp -t uninstall-opencode-XXXXXX.json)"
  jq 'del(.permission.bash["make -f agents/memory/scripts/Makefile wipe *"]) |
      del(.permission.bash["make -f agents/memory/scripts/Makefile set-project *"])' \
    "$tmp_json" > "${tmp_json}.new" && mv "${tmp_json}.new" "$tmp_json"

  # Remove custom-tool permission rules
  tmp_json="$(mktemp -t uninstall-opencode-XXXXXX.json)"
  jq 'del(.permission.memory_node, .permission.memory_rel, .permission.memory_query,
         .permission.memory_audit, .permission.memory_seed, .permission.memory_status)' \
    "$tmp_json" > "${tmp_json}.new" && mv "${tmp_json}.new" "$tmp_json"

  mv "$tmp_json" "$OPENCODE_JSON"
  echo "reverted: $OPENCODE_JSON (removed .project protection, bash deny rules, custom tool perms)"
fi

# ---- 4. reverse .gitignore patches ----
GITIGNORE="$PROJECT_ROOT/.gitignore"
if [ ! -f "$GITIGNORE" ]; then
  echo "skip (not found): $GITIGNORE"
else
  # Remove the 3 lines plus the comment header that install.sh added.
  if grep -qF "agents/memory/.project" "$GITIGNORE" \
     || grep -qF "agents/memory/runtime/.env" "$GITIGNORE" \
     || grep -qF "agents/memory/seed/*.yaml" "$GITIGNORE"; then
    # Use a Python helper for safe multi-line deletion.
    python3 - "$GITIGNORE" <<'PY'
import sys, re
p = sys.argv[1]
with open(p) as fh: lines = fh.readlines()
out, skip = [], False
patterns = (
    "agents/memory/.project",
    "agents/memory/runtime/.env",
    "agents/memory/seed/*.yaml",
    "# agents/memory module (per-machine / per-project state)",
)
for line in lines:
    if any(pat in line for pat in patterns):
        # Drop the trailing blank line that preceded the header (if present)
        continue
    out.append(line)
# Collapse the resulting double blank lines
collapsed = []
prev_blank = False
for line in out:
    is_blank = (line.strip() == "")
    if is_blank and prev_blank:
        continue
    collapsed.append(line)
    prev_blank = is_blank
with open(p, "w") as fh: fh.writelines(collapsed)
PY
    echo "reverted: $GITIGNORE (removed 3 patterns + header)"
  else
    echo "skip (no agents/memory lines found): $GITIGNORE"
  fi
fi

# ---- 5. leave .project + runtime/.env + seed/*.yaml alone ----
# These are per-machine / per-project state. The human deletes them
# manually if they want to wipe the install.

cat <<EOF

uninstall.sh: done. Removed opencode-stubs and reversed patches.
agents/memory/ itself is untouched. To remove it:
  git rm -r agents/memory
EOF
