#!/usr/bin/env bash
# Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.

# agents/memory/scripts/schema.sh
# Reads memory/config/config.yaml and exposes the entity_types schema.
# Caches the parsed label list in runs/schema.cache to avoid re-parsing on
# every write.
#
# Usage:
#   schema.sh labels                      # print the list of labels
#   schema.sh describe <Label>            # print the description of a label
#   schema.sh validate <Label>            # exit 0 if label is in schema, 1 if not
#   schema.sh all                         # print "Label: description" for each

set -euo pipefail

# --- locate project root (the dir that contains memory/) ---
_find_root() {
  local d="${1:-$PWD}"
  while [ "$d" != "/" ]; do
    [ -d "$d/agents/memory" ] && [ -f "$d/agents/memory/runtime/config/config.yaml" ] && [ -f "$d/agents/memory/scripts/memory.sh" ] && { echo "$d"; return 0; }
    d="$(dirname "$d")"
  done
  return 1
}

ROOT="$(_find_root "$PWD")" || { echo "schema.sh: cannot find project root (no agents/memory/runtime/config/config.yaml or agents/memory/scripts/memory.sh)" >&2; exit 2; }
CONFIG="$ROOT/agents/memory/runtime/config/config.yaml"
CACHE_DIR="$ROOT/runs"
CACHE="$CACHE_DIR/schema.cache"

mkdir -p "$CACHE_DIR"

# --- mtime helper (BSD / GNU compatible) ---
_mtime() {
  stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0
}

# --- parse the YAML into a label | description cache ---
# We use a Python one-liner because the project ships Python 3 via uv, and
# writing a portable awk that handles YAML quoting edge cases is fragile.
# The python uses only the standard library.
parse_yaml_to_cache() {
  python3 - "$CONFIG" <<'PY'
import re, sys

path = sys.argv[1]
text = open(path).read()

# Find each "- name: ..." block, capture name and (optional) description.
# The config uses a flat structure: each entity_type is a 2-space-indented
# list item with a 4-space-indented description below.
pattern = re.compile(
    r'^-\s*name:\s*"?([A-Za-z]+)"?\s*\n'
    r'(?:\s*description:\s*"?(.+?)"?\s*(?=\n\s*\n|-\s|\Z))?',
    re.MULTILINE | re.DOTALL,
)

# The config.yaml format we ship has description on the line after name.
# A simpler line-based approach is enough:
out = []
lines = text.splitlines()
i = 0
while i < len(lines):
    line = lines[i]
    m = re.match(r'^\s*-\s*name:\s*"?([A-Za-z]+)"?', line)
    if m:
        label = m.group(1)
        desc = ""
        # description may be on the next non-empty line
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            dm = re.match(r'^\s*description:\s*"?(.+?)"?\s*$', nxt)
            if dm:
                desc = dm.group(1)
                # Unescape literal \n
                desc = desc.replace('\\n', ' ')
                desc = re.sub(r'\s+', ' ', desc).strip()
                break
            # If we hit another list item or top-level key, stop.
            if re.match(r'^\s*-\s*name:', nxt) or re.match(r'^[A-Za-z]', nxt):
                break
            j += 1
        out.append(f"{label}|{desc}")
        i = j + 1
        continue
    i += 1

with open("__cache__", "w") as f:
    f.write("\n".join(out) + "\n")
PY
}

if [ ! -f "$CACHE" ] || [ "$(_mtime "$CACHE")" -lt "$(_mtime "$CONFIG")" ]; then
  (
    cd "$CACHE_DIR"
    parse_yaml_to_cache
    mv -f "__cache__" "$CACHE"
  )
fi

# --- subcommands ---
cmd="${1:-labels}"
shift || true

case "$cmd" in
  labels)
    cut -d'|' -f1 "$CACHE"
    ;;
  describe)
    label="${1:?usage: schema.sh describe <Label>}"
    line="$(awk -F'|' -v L="$label" '$1==L {print; exit}' "$CACHE")"
    if [ -z "$line" ]; then
      echo "schema.sh: unknown label '$label' (not in $CONFIG)" >&2
      exit 1
    fi
    echo "${line#*|}"
    ;;
  validate)
    label="${1:?usage: schema.sh validate <Label>}"
    if awk -F'|' -v L="$label" '$1==L {found=1; exit} END{exit !found}' "$CACHE"; then
      exit 0
    else
      echo "schema.sh: '$label' is not in schema (see $CONFIG)" >&2
      exit 1
    fi
    ;;
  all)
    while IFS='|' read -r lbl desc; do
      printf '%s: %s\n' "$lbl" "$desc"
    done < "$CACHE"
    ;;
  *)
    echo "schema.sh: unknown subcommand '$cmd'" >&2
    echo "usage: schema.sh {labels|describe <L>|validate <L>|all}" >&2
    exit 2
    ;;
esac
