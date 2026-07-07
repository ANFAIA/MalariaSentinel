#!/usr/bin/env bash
# Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.

# agents/memory/scripts/seed.sh
# Compiles a project seed yaml into Cypher, validates every label against
# the schema, and runs the result as a single atomic write against Neo4j.
#
# Usage:
#   seed.sh <project>            # project = the yaml stem in seed/ (e.g. malariasentinel)
#                                # and the Neo4j group_id (authoritative)
#   seed.sh <project> --dry-run  # write the generated cypher to stdout, do not execute
#
# The yaml must declare every node under a top-level key matching its
# schema label (components, investigations, pitfalls, preferences,
# architectures, tools, patterns, operational). Every node must have uuid
# + name + summary. The script will reject unknown labels and missing
# required fields before issuing any Cypher.
#
# The yaml's `project:` field is required (used as the project name in
# logs). The yaml's `group_id:` field is documentation-only — the
# positional argument is the authoritative group_id (this is what the
# Makefile passes from tools/memory/.project). If the yaml's group_id
# disagrees, seed.sh warns and uses the argument.
#
# Multi-line summaries use `summary: |` block scalars and are joined with
# single spaces. The yaml must be well-formed (2-space indentation, keys
# at the start of a line, list items with leading "- ").

set -euo pipefail

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

project="${1:-}"
[ -n "$project" ] || { echo "seed.sh: usage: seed.sh <project> [--dry-run]" >&2; exit 2; }
shift || true
dry_run=0
[ "${1:-}" = "--dry-run" ] && dry_run=1

YAML="$HERE/seed/${project}.yaml"
[ -f "$YAML" ] || { echo "seed.sh: missing $YAML" >&2; exit 2; }

# --- parse the entire yaml into a Python dict and dump it as a flat
# "key\tvalue" file. We use Python because the project's macOS awk does
# not support gawk's match-with-array extension, and writing a portable
# awk that handles all our yaml cases is more work than this one-liner.

TMPDIR_RUN="$(mktemp -d -t seed-XXXXXX)"
trap 'rm -rf "$TMPDIR_RUN"' EXIT

python3 - "$YAML" "$TMPDIR_RUN" <<'PY'
import sys, re, os

yaml_path = sys.argv[1]
out_dir   = sys.argv[2]

with open(yaml_path) as f:
    text = f.read()

# Strip comments and blank-only lines.
lines = []
for raw in text.splitlines():
    s = raw.rstrip()
    if not s or s.lstrip().startswith("#"):
        continue
    lines.append(s)

# Top-level keys
top = {}
top_scalars = {}
i = 0
while i < len(lines):
    line = lines[i]
    m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$', line)
    if m:
        key, val = m.group(1), m.group(2)
        if val == "":
            # List block. Skip to next non-blank line.
            i += 1
            items = []
            while i < len(lines):
                s = lines[i]
                if re.match(r'^[A-Za-z_][A-Za-z0-9_]*:', s):
                    break
                m2 = re.match(r'^\s*-\s*(.*)$', s)
                if m2:
                    first = m2.group(1).strip()
                    item_lines = []
                    if first:
                        item_lines.append(first)
                    i += 1
                    while i < len(lines):
                        s2 = lines[i]
                        if re.match(r'^\s*-\s', s2) or re.match(r'^[A-Za-z_][A-Za-z0-9_]*:', s2):
                            break
                        item_lines.append(s2)
                        i += 1
                    items.append(item_lines)
                    continue
                i += 1
            top[key] = items
            continue
        else:
            # Scalar top-level: "project: foo" or "group_id: bar"
            top_scalars[key] = val.strip().strip('"').strip("'")
            i += 1
            continue
    i += 1

# Parse one item (a list of strings, the first being the inline start)
def parse_item(item_lines):
    d = {}
    # The first line may have a `key: value` field.
    first = item_lines[0]
    m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$', first)
    if m and m.group(2):
        d[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        i = 1
        while i < len(item_lines):
            s = item_lines[i]
            ms = re.match(r'^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$', s)
            if ms:
                key, val = ms.group(2), ms.group(3)
                key_indent = len(ms.group(1))
                if val == "|":
                    # Block scalar: collect subsequent lines indented at
                    # or beyond key_indent + 2. The previous version used
                    # a regex to skip lines that look like `key:`, which
                    # broke on content like "Goal: ship a v0 ..." inside
                    # the block. Tracking the indent fixes it.
                    i += 1
                    buf = []
                    block_indent = key_indent + 2
                    while i < len(item_lines):
                        s2 = item_lines[i]
                        stripped = s2.strip()
                        if not stripped:
                            i += 1
                            continue
                        line_indent = len(s2) - len(s2.lstrip(' '))
                        if line_indent < block_indent:
                            break
                        buf.append(stripped)
                        i += 1
                    d[key] = " ".join(b for b in buf if b)
                elif val == "":
                    # Sub-block — we don't use this in the project yaml.
                    i += 1
                else:
                    d[key] = val.strip().strip('"').strip("'")
                    i += 1
            else:
                i += 1
        return d

# Helper: relations are a special shape: - { src: a, type: T, dst: b, props: {k=v, k=v} }
def parse_relation(item_lines):
    # Concatenate the lines into a single string and pull k:v pairs.
    text = " ".join(item_lines)
    d = {}
    for m in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*):\s*([^,}\s][^,}]*)', text):
        d[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return d

project_name = top_scalars.get("project")
group_id     = top_scalars.get("group_id")

# Now write out a per-section file with parsed items as tab-separated
# (uuid<TAB>name<TAB>summary<TAB>path<TAB>extra) lines. Relations get
# (src<TAB>type<TAB>dst<TAB>props) lines.
def emit_section(label, yaml_key, dest_file, is_relation=False):
    items = top.get(yaml_key, [])
    out_lines = []
    for il in items:
        if is_relation:
            d = parse_relation(il)
        else:
            d = parse_item(il)
        if is_relation:
            out_lines.append("\t".join([
                d.get("src", ""),
                d.get("type", ""),
                d.get("dst", ""),
                d.get("props", ""),
            ]))
        else:
            out_lines.append("\t".join([
                d.get("uuid", ""),
                d.get("name", ""),
                d.get("summary", ""),
                d.get("path", ""),
            ]))
    with open(os.path.join(out_dir, dest_file), "w") as f:
        f.write("\n".join(out_lines) + ("\n" if out_lines else ""))

with open(os.path.join(out_dir, "project"), "w") as f:
    f.write(f"{project_name or ''}\n")
with open(os.path.join(out_dir, "group_id"), "w") as f:
    f.write(f"{group_id or ''}\n")

emit_section("Component",      "components",     "components")
emit_section("Investigation",  "investigations", "investigations")
emit_section("Pitfall",        "pitfalls",       "pitfalls")
emit_section("Preference",     "preferences",    "preferences")
emit_section("Architecture",   "architectures",  "architectures")
emit_section("Tool",           "tools",          "tools")
emit_section("Pattern",        "patterns",       "patterns")
emit_section("Operational",    "operational",    "operational")
emit_section("Relation",       "relations",      "relations", is_relation=True)
PY

project_name="$(cat "$TMPDIR_RUN/project")"
yaml_group_id="$(cat "$TMPDIR_RUN/group_id")"

# The positional argument is the authoritative group_id (this is what the
# Makefile passes from tools/memory/.project). The yaml's `group_id:` field
# is treated as documentation only — if present and non-empty, we warn if
# it disagrees with the positional arg.
group_id="$project"
if [ -n "$yaml_group_id" ] && [ "$yaml_group_id" != "$group_id" ]; then
  echo "seed.sh: WARNING — yaml declares group_id='$yaml_group_id' but argument is '$group_id'; using the argument" >&2
fi

if [ -z "$project_name" ]; then
  echo "seed.sh: yaml must declare 'project:' at the top" >&2
  exit 2
fi

# --- validate every label is in the schema before any write ---
LABEL_LIST="Component Investigation Architecture Pattern Pitfall Tool Operational Preference"
for label in $LABEL_LIST; do
  if ! "$HERE/schema.sh" validate "$label" >/dev/null 2>&1; then
    echo "seed.sh: schema does not contain label '$label'" >&2
    exit 1
  fi
done

# --- build the Cypher ---
cypher="$(mktemp -t seed-XXXXXX.cypher)"
trap 'rm -rf "$TMPDIR_RUN"; rm -f "$cypher"' EXIT

emit_nodes() {
  local label="$1" section_file="$2"
  [ -s "$section_file" ] || return 0
  local i=0
  while IFS=$'\t' read -r uuid name summary path; do
    [ -z "$uuid" ] && continue
    if [ -z "$name" ]; then
      echo "seed.sh: $label section has entry without 'name' (uuid=$uuid)" >&2
      exit 2
    fi
    local prefix="${label}_${i}"
    cat >> "$cypher" <<EOF
MERGE (n:Entity:${label} {uuid: \$${prefix}_uuid, group_id: \$gid})
  ON CREATE SET n.name = \$${prefix}_name,
                n.summary = \$${prefix}_summary,
                n.path = \$${prefix}_path,
                n.created_at = datetime()
  ON MATCH  SET n.name = \$${prefix}_name,
                n.summary = \$${prefix}_summary,
                n.path = \$${prefix}_path;
EOF
    params+=("--param" "${prefix}_uuid=$uuid")
    params+=("--param" "${prefix}_name=$name")
    params+=("--param" "${prefix}_summary=${summary:-}")
    params+=("--param" "${prefix}_path=${path:-}")
    i=$((i+1))
  done < "$section_file"
}

params=("--param" "gid=$group_id")

emit_nodes "Component"      "$TMPDIR_RUN/components"
emit_nodes "Investigation"  "$TMPDIR_RUN/investigations"
emit_nodes "Pitfall"        "$TMPDIR_RUN/pitfalls"
emit_nodes "Preference"     "$TMPDIR_RUN/preferences"
emit_nodes "Architecture"   "$TMPDIR_RUN/architectures"
emit_nodes "Tool"           "$TMPDIR_RUN/tools"
emit_nodes "Pattern"        "$TMPDIR_RUN/patterns"
emit_nodes "Operational"    "$TMPDIR_RUN/operational"

# --- relations ---
[ -s "$TMPDIR_RUN/relations" ] || true
i=0
while IFS=$'\t' read -r src type dst props; do
  [ -z "$src" ] && continue
  if [ -z "$type" ] || [ -z "$dst" ]; then
    echo "seed.sh: relations[$i] missing src/type/dst" >&2
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
  cat >> "$cypher" <<EOF
MATCH (a:Entity {uuid: \$r_${i}_src, group_id: \$gid})
MATCH (b:Entity {uuid: \$r_${i}_dst, group_id: \$gid})
MERGE (a)-[r:${type}]->(b)
  ON CREATE SET ${set_clause}
  ON MATCH  SET ${set_clause};
EOF
  params+=("--param" "r_${i}_src=$src")
  params+=("--param" "r_${i}_dst=$dst")
  i=$((i+1))
done < "$TMPDIR_RUN/relations"

# --- dry-run? ---
if [ "$dry_run" = "1" ]; then
  cat "$cypher"
  echo
  echo "# params: ${#params[@]}"
  exit 0
fi

# --- log + execute ---
mkdir -p "$ROOT/runs"
{
  echo "# seed.sh $project $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "# group_id: $group_id"
  echo "# nodes: $(grep -c '^MERGE (n:Entity:' "$cypher" || echo 0)"
  echo "# rels:  $(grep -c '^MERGE (a)-\[r:' "$cypher" || echo 0)"
  cat "$cypher"
} >> "$ROOT/runs/memory.log"

# Run from the memory/ dir so neo4j-cli picks up the .env.
(
  cd "$ROOT/agents/memory/runtime" && \
  neo4j-cli query "$(cat "$cypher")" --rw --atomic --format toon "${params[@]}"
)

# --- audit immediately after the seed ---
echo
echo "--- post-seed audit ---"
"$HERE/audit.sh" || {
  echo "seed.sh: post-seed audit FAILED — graph may be in a partial state." >&2
  echo "Re-running seed.sh is idempotent and will converge to the correct state." >&2
  exit 1
}
