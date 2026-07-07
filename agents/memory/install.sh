#!/usr/bin/env bash
# agents/memory/install.sh
# THE installer for the agents/memory module. Wires up the module into
# the surrounding project: copies opencode-stubs (skill + 6 tools),
# generates per-project state (.project, .env), patches opencode.json
# and .gitignore. Idempotent — re-running is safe.
#
# Usage:
#   bash agents/memory/install.sh                                  # interactive
#   bash agents/memory/install.sh --project myproj                 # non-interactive slug
#   bash agents/memory/install.sh --config /path/to/mem.env        # all vars in a file
#   bash agents/memory/install.sh --project myproj \
#        --openai-key sk-... --neo4j-password ... --yes
#
# Config file format (KEY=VALUE per line, # for comments):
#   PROJECT=myproj
#   OPENAI_API_KEY=sk-...
#   NEO4J_PASSWORD=...
#   NEO4J_USER=neo4j                  # default: neo4j
#   GRAPHITI_GROUP_ID=myproj          # default: same as PROJECT
#   MODEL_NAME=gpt-4o-mini            # default: gpt-4o-mini
#   EMBEDDER_MODEL=text-embedding-3-small  # default

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# The module is at <project_root>/agents/memory/, so the project root is
# two levels up from HERE. (If a user invokes install.sh from elsewhere
# via absolute path, HERE still resolves to the script's own directory.)
PROJECT_ROOT="$(cd "$HERE/../.." && pwd)"

# ---- argument parsing ----
PROJECT=""
OPENAI_KEY=""
NEO4J_USER="neo4j"
NEO4J_PASSWORD=""
GRAPHITI_GROUP_ID=""
MODEL_NAME="gpt-4o-mini"
EMBEDDER_MODEL="text-embedding-3-small"
CONFIG_FILE=""
ASSUME_YES=0

usage() {
  sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)        PROJECT="${2:-}"; shift 2 ;;
    --openai-key)     OPENAI_KEY="${2:-}"; shift 2 ;;
    --neo4j-user)     NEO4J_USER="${2:-}"; shift 2 ;;
    --neo4j-password) NEO4J_PASSWORD="${2:-}"; shift 2 ;;
    --graphiti-group) GRAPHITI_GROUP_ID="${2:-}"; shift 2 ;;
    --model)          MODEL_NAME="${2:-}"; shift 2 ;;
    --embedder)       EMBEDDER_MODEL="${2:-}"; shift 2 ;;
    --config)         CONFIG_FILE="${2:-}"; shift 2 ;;
    -y|--yes)         ASSUME_YES=1; shift ;;
    -h|--help)        usage; exit 0 ;;
    *) echo "install.sh: unknown flag '$1'" >&2; usage; exit 2 ;;
  esac
done

# ---- load config file if given (KEY=VALUE) ----
if [ -n "$CONFIG_FILE" ]; then
  if [ ! -f "$CONFIG_FILE" ]; then
    echo "install.sh: --config file not found: $CONFIG_FILE" >&2
    exit 2
  fi
  while IFS='=' read -r key value; do
    # skip blanks/comments
    case "$key" in ''|\#*) continue ;; esac
    key="$(echo "$key" | tr -d '[:space:]')"
    value="${value%%#*}"   # strip trailing comments
    value="$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    case "$key" in
      PROJECT)         PROJECT="$value" ;;
      OPENAI_API_KEY)  OPENAI_KEY="$value" ;;
      NEO4J_USER)      NEO4J_USER="$value" ;;
      NEO4J_PASSWORD)  NEO4J_PASSWORD="$value" ;;
      GRAPHITI_GROUP_ID) GRAPHITI_GROUP_ID="$value" ;;
      MODEL_NAME)      MODEL_NAME="$value" ;;
      EMBEDDER_MODEL)  EMBEDDER_MODEL="$value" ;;
      *) echo "install.sh: ignoring unknown key '$key' in $CONFIG_FILE" >&2 ;;
    esac
  done < "$CONFIG_FILE"
fi

# ---- interactive prompts (skipped if --yes or all set) ----
prompt() {
  local var_name="$1" prompt_text="$2" current_value="${3:-}" is_secret="${4:-0}"
  if [ -n "$current_value" ]; then
    eval "$var_name=\"\$current_value\""
    return
  fi
  if [ "$ASSUME_YES" = "1" ]; then
    echo "install.sh: $var_name not set and --yes given; refusing to prompt" >&2
    exit 2
  fi
  if [ "$is_secret" = "1" ]; then
    read -r -s -p "$prompt_text: " value < /dev/tty && echo
  else
    read -r -p "$prompt_text [$current_value]: " value < /dev/tty
    value="${value:-$current_value}"
  fi
  eval "$var_name=\"\$value\""
}

prompt PROJECT        "Project slug (Neo4j group_id, lowercase, e.g. 'myorg-myapp')" "$PROJECT" 0
# GRAPHITI_GROUP_ID defaults to the project slug; skip prompt if --yes and no override.
if [ -z "$GRAPHITI_GROUP_ID" ] && [ "$ASSUME_YES" = "1" ]; then
  GRAPHITI_GROUP_ID="$PROJECT"
fi
prompt GRAPHITI_GROUP_ID "Graphiti group_id (default: same as project slug)" "$GRAPHITI_GROUP_ID" 0
prompt NEO4J_USER     "Neo4j user" "$NEO4J_USER" 0
prompt NEO4J_PASSWORD "Neo4j password" "$NEO4J_PASSWORD" 1
prompt OPENAI_KEY     "OpenAI API key" "$OPENAI_KEY" 1
prompt MODEL_NAME     "OpenAI model name" "$MODEL_NAME" 0
prompt EMBEDDER_MODEL "OpenAI embedder model" "$EMBEDDER_MODEL" 0

# Defaults: GRAPHITI_GROUP_ID = PROJECT if not set
[ -n "$GRAPHITI_GROUP_ID" ] || GRAPHITI_GROUP_ID="$PROJECT"

# ---- validate ----
slug_ok() {
  echo "$1" | grep -qE '^[a-z0-9](-?[a-z0-9])*$' || {
    echo "install.sh: invalid slug '$1' (must match ^[a-z0-9](-?[a-z0-9])*$)" >&2
    exit 2
  }
}
slug_ok "$PROJECT"
slug_ok "$GRAPHITI_GROUP_ID"
[ -n "$NEO4J_PASSWORD" ] || { echo "install.sh: --neo4j-password (or NEO4J_PASSWORD) is required" >&2; exit 2; }
[ -n "$OPENAI_KEY" ]     || { echo "install.sh: --openai-key (or OPENAI_API_KEY) is required" >&2; exit 2; }

# ---- sanity: opencode.json and .gitignore must exist ----
OPENCODE_JSON="$PROJECT_ROOT/opencode.json"
GITIGNORE="$PROJECT_ROOT/.gitignore"
[ -f "$OPENCODE_JSON" ] || { echo "install.sh: $OPENCODE_JSON not found (run from a project root)" >&2; exit 2; }
[ -f "$GITIGNORE" ]     || { echo "install.sh: $GITIGNORE not found" >&2; exit 2; }

# ---- write .project ----
PROJECT_FILE="$HERE/.project"
if [ -f "$PROJECT_FILE" ]; then
  existing="$(tr -d '[:space:]' < "$PROJECT_FILE")"
  if [ "$existing" != "$PROJECT" ]; then
    if [ "$ASSUME_YES" != "1" ]; then
      read -r -p "agents/memory/.project already set to '$existing'. Overwrite with '$PROJECT'? [y/N] " ans < /dev/tty
      case "${ans:-N}" in y|Y|yes|YES) ;; *) echo "aborted."; exit 1 ;; esac
    fi
  fi
fi
printf '%s\n' "$PROJECT" > "$PROJECT_FILE"
echo "wrote $PROJECT_FILE -> $PROJECT"

# ---- generate runtime/.env from .env.example ----
ENV_FILE="$HERE/runtime/.env"
ENV_EXAMPLE="$HERE/runtime/.env.example"
[ -f "$ENV_EXAMPLE" ] || { echo "install.sh: missing $ENV_EXAMPLE" >&2; exit 2; }

if [ -f "$ENV_FILE" ]; then
  echo "install.sh: $ENV_FILE already exists; leaving it (delete it to regenerate)"
else
  {
    sed \
      -e "s|^NEO4J_USER=.*|NEO4J_USER=$NEO4J_USER|" \
      -e "s|^NEO4J_PASSWORD=.*|NEO4J_PASSWORD=$NEO4J_PASSWORD|" \
      -e "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=$OPENAI_KEY|" \
      -e "s|^GRAPHITI_GROUP_ID=.*|GRAPHITI_GROUP_ID=$GRAPHITI_GROUP_ID|" \
      -e "s|^MODEL_NAME=.*|MODEL_NAME=$MODEL_NAME|" \
      -e "s|^EMBEDDER_MODEL=.*|EMBEDDER_MODEL=$EMBEDDER_MODEL|" \
      "$ENV_EXAMPLE"
  } > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "wrote $ENV_FILE"
fi

# ---- copy opencode-stubs/skills -> <root>/.agents/skills/ ----
SKILL_SRC="$HERE/opencode-stubs/skills/project-memory/SKILL.md"
SKILL_DST_DIR="$PROJECT_ROOT/.agents/skills/project-memory"
SKILL_DST="$SKILL_DST_DIR/SKILL.md"
[ -f "$SKILL_SRC" ] || { echo "install.sh: missing $SKILL_SRC" >&2; exit 2; }
if [ -e "$SKILL_DST" ]; then
  echo "install.sh: skip (already exists): $SKILL_DST"
else
  mkdir -p "$SKILL_DST_DIR"
  cp "$SKILL_SRC" "$SKILL_DST"
  echo "copied: $SKILL_DST"
fi

# ---- copy opencode-stubs/tools -> <root>/.opencode/tools/ ----
TOOLS_SRC_DIR="$HERE/opencode-stubs/tools"
TOOLS_DST_DIR="$PROJECT_ROOT/.opencode/tools"
[ -d "$TOOLS_SRC_DIR" ] || { echo "install.sh: missing $TOOLS_SRC_DIR" >&2; exit 2; }
mkdir -p "$TOOLS_DST_DIR"
for src in "$TOOLS_SRC_DIR"/*.ts; do
  [ -f "$src" ] || continue
  base="$(basename "$src")"
  dst="$TOOLS_DST_DIR/$base"
  if [ -e "$dst" ]; then
    echo "install.sh: skip (already exists): $dst"
  else
    cp "$src" "$dst"
    echo "copied: $dst"
  fi
done

# ---- patch opencode.json (permission rules, idempotent) ----
command -v jq >/dev/null 2>&1 || { echo "install.sh: 'jq' is required to patch opencode.json" >&2; exit 2; }

tmp_json="$(mktemp -t install-opencode-XXXXXX.json)"
trap 'rm -f "$tmp_json" "${tmp_json}.new"' EXIT
cp "$OPENCODE_JSON" "$tmp_json"

# Add edit-protection for .project (under permission.edit.<path>: ask)
jq --arg path "agents/memory/.project" \
   '.permission.edit = (.permission.edit // {}) + {($path): "ask"}' \
   "$tmp_json" > "${tmp_json}.new" && mv "${tmp_json}.new" "$tmp_json"

# Add bash deny rules for wipe + set-project
deny_target="make -f agents/memory/scripts/Makefile"
jq --arg target "$deny_target" \
   '.permission.bash = (.permission.bash // {}) + {
     ($target + " wipe *"): "deny",
     ($target + " set-project *"): "deny"
   }' \
   "$tmp_json" > "${tmp_json}.new" && mv "${tmp_json}.new" "$tmp_json"

# Add custom-tool permission rules
jq '.permission = (.permission // {}) + {
     "memory_node":   "ask",
     "memory_rel":    "ask",
     "memory_query":  "allow",
     "memory_audit":  "allow",
     "memory_seed":   "ask",
     "memory_status": "allow"
   }' \
   "$tmp_json" > "${tmp_json}.new" && mv "${tmp_json}.new" "$tmp_json"

mv "$tmp_json" "$OPENCODE_JSON"
# Post-process: jq reformats top-level arrays to multi-line on every pass
# (e.g. "instructions": ["..."] -> "instructions": [\n  "..."\n]). For
# idempotency, compact any top-level string array with one element.
python3 - "$OPENCODE_JSON" <<'PY'
import json, sys, re
p = sys.argv[1]
with open(p) as fh: data = json.load(fh)
# Find top-level string-array keys and emit them in compact form.
s = json.dumps(data, indent=2)
# Compact arrays of strings of length 1, only at the top level. We do
# this by re-walking the original parsed object and overriding just the
# top-level keys that are short string arrays.
out_lines = []
i = 0
# Easier: regex the output and replace specific known keys.
# We compact "instructions" (the only single-element string array we
# expect at the top level), and leave everything else as jq wrote it.
s2 = re.sub(
    r'("instructions":\s*)\[\n\s+("[^"]+")\n\s+\]',
    r'\1[\2]',
    s,
)
if s2 != s:
    with open(p, "w") as fh: fh.write(s2 + "\n")
PY
echo "patched: $OPENCODE_JSON (permission rules for edit, bash deny, custom tools)"

# ---- patch .gitignore (idempotent) ----
# Add a single header + the three patterns, but only if at least one
# is missing. The header is a one-time addition; subsequent runs
# append only the patterns that are missing.
GITIGNORE_HEADER="# agents/memory module (per-machine / per-project state)"
GITIGNORE_PATTERNS=(
  "agents/memory/.project"
  "agents/memory/runtime/.env"
  "agents/memory/seed/*.yaml"
)

# Decide if any pattern is missing
missing=()
for p in "${GITIGNORE_PATTERNS[@]}"; do
  if ! grep -qxF "$p" "$GITIGNORE" 2>/dev/null; then
    missing+=("$p")
  fi
done

if [ "${#missing[@]}" -eq 0 ]; then
  echo "install.sh: .gitignore already has all 3 agents/memory patterns"
else
  {
    if ! grep -qxF "$GITIGNORE_HEADER" "$GITIGNORE" 2>/dev/null; then
      printf '\n%s\n' "$GITIGNORE_HEADER"
    fi
    for p in "${missing[@]}"; do
      printf '%s\n' "$p"
    done
  } >> "$GITIGNORE"
  for p in "${missing[@]}"; do
    echo "appended to .gitignore: $p"
  done
fi

# ---- done ----
cat <<EOF

install.sh: done.

Next steps:
  1. Restart OpenCode so it picks up the new skill and custom tools.
  2. Cold-start the stack:
       make -f agents/memory/scripts/Makefile bootstrap
  3. Verify:
       make -f agents/memory/scripts/Makefile show-project
       make -f agents/memory/scripts/Makefile status
       make -f agents/memory/scripts/Makefile audit
  4. (Optional) Edit agents/memory/seed/<project>.yaml to seed initial
     nodes, then:
       make -f agents/memory/scripts/Makefile seed
EOF
