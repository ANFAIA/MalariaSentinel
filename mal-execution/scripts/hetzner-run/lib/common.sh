#!/usr/bin/env bash
# hetzner-run — common helpers
# Source-only; no `set` directives here (the main script handles them).

# Resolve the directory of the hetzner-run package, regardless of how the
# top-level dispatcher was invoked (symlink, absolute, or relative path).
_hetzner_run_self_dir() {
  local src="${BASH_SOURCE[0]}"
  while [[ -h "$src" ]]; do
    local dir
    dir="$(cd -P "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$dir/$src"
  done
  local lib_dir
  lib_dir="$(cd -P "$(dirname "$src")" && pwd)"
  (cd "$lib_dir/.." && pwd)
}
HETZNER_RUN_ROOT="$(_hetzner_run_self_dir)"
HETZNER_RUN_LIB="$HETZNER_RUN_ROOT/lib"
HETZNER_RUN_CLOUD_INIT="$HETZNER_RUN_ROOT/cloud-init.yaml"
HETZNER_RUN_CACHE_DIR="${HETZNER_RUN_CACHE_DIR:-$HOME/.cache/hetzner-run}"
export HETZNER_RUN_ROOT HETZNER_RUN_LIB HETZNER_RUN_CLOUD_INIT HETZNER_RUN_CACHE_DIR

# --- logging ---------------------------------------------------------------

_log_ts() { date '+%Y-%m-%dT%H:%M:%S%z'; }

log_info()  { printf '[%s] [info]  %s\n'  "$(_log_ts)" "$*" >&2; }
log_warn()  { printf '[%s] [warn]  %s\n'  "$(_log_ts)" "$*" >&2; }
log_error() { printf '[%s] [error] %s\n'  "$(_log_ts)" "$*" >&2; }
log_debug() {
  if [[ "${HETZNER_RUN_DEBUG:-0}" == "1" ]]; then
    printf '[%s] [debug] %s\n' "$(_log_ts)" "$*" >&2
  fi
}

die() {
  log_error "$*"
  exit 1
}

# --- dependency check ------------------------------------------------------

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "required command not found: $cmd"
}

ensure_jq() {
  require_cmd jq
}

ensure_hcloud() {
  require_cmd hcloud
}

# --- hcloud wrapper --------------------------------------------------------
# All real hcloud calls go through hcloud_run so dry-run can intercept them.
# In dry-run mode, hcloud_run prints the command to stderr and returns 0
# without executing it.

hcloud_run() {
  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    printf '[dry-run] hcloud %s\n' "$*" >&2
    return 0
  fi
  ensure_hcloud
  hcloud "$@"
}

# Run hcloud with --output json. In dry-run mode, prints the command and
# returns an empty JSON object so downstream jq pipelines don't error.
hcloud_json() {
  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    printf '[dry-run] hcloud %s\n' "$*" >&2
    echo "{}"
    return 0
  fi
  ensure_hcloud
  ensure_jq
  hcloud "$@" --output json
}

# --- SSH key detection -----------------------------------------------------

# Auto-detect the local SSH private key path. Returns the first one that
# exists. Prints the first candidate path even if neither exists (caller
# should validate before use).
detect_ssh_key_path() {
  for candidate in \
    "${HETZNER_RUN_SSH_KEY_PATH:-$HOME/.ssh/id_ed25519}" \
    "$HOME/.ssh/id_rsa"; do
    if [[ -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  printf '%s\n' "${HETZNER_RUN_SSH_KEY_PATH:-$HOME/.ssh/id_ed25519}"
  return 1
}

# Resolve a usable ssh key name for hcloud. Priority:
#   1. $1 (caller-supplied --ssh-key)
#   2. env HETZNER_RUN_SSH_KEY_NAME
#   3. literal default "davidflorezmazuera@gmail.com"
resolve_ssh_key_name() {
  local explicit="${1:-}"
  if [[ -n "$explicit" ]]; then
    printf '%s\n' "$explicit"
    return 0
  fi
  if [[ -n "${HETZNER_RUN_SSH_KEY_NAME:-}" ]]; then
    printf '%s\n' "$HETZNER_RUN_SSH_KEY_NAME"
    return 0
  fi
  printf '%s\n' "davidflorezmazuera@gmail.com"
}

# Build an ssh -i option if we have a private key file.
ssh_identity_args() {
  local key_path
  key_path="$(detect_ssh_key_path 2>/dev/null || true)"
  if [[ -n "$key_path" && -f "$key_path" ]]; then
    printf -- '-i %s ' "$key_path"
  fi
}

# --- metadata cache --------------------------------------------------------
# Each VM is described in $HETZNER_RUN_CACHE_DIR/<name>.json so non-start
# commands don't need to round-trip hcloud for the IP.

cache_path_for() {
  local name="$1"
  printf '%s/%s.json\n' "$HETZNER_RUN_CACHE_DIR" "$name"
}

write_cache() {
  local name="$1" ip="$2" type="$3" location="$4" started_at="$5"
  mkdir -p "$HETZNER_RUN_CACHE_DIR"
  jq -n \
    --arg name "$name" \
    --arg ip "$ip" \
    --arg type "$type" \
    --arg location "$location" \
    --arg started_at "$started_at" \
    '{name:$name, ip:$ip, type:$type, location:$location, started_at:$started_at}' \
    > "$(cache_path_for "$name")"
}

read_cache_field() {
  local name="$1" field="$2"
  local path
  path="$(cache_path_for "$name")"
  [[ -f "$path" ]] || return 1
  jq -r --arg f "$field" '.[$f] // empty' "$path"
}

remove_cache() {
  local name="$1"
  rm -f "$(cache_path_for "$name")"
}

# --- cost calculator -------------------------------------------------------

# Price table (€/h) for known server types. Add new types here.
PRICE_TABLE_EUR_PER_HOUR='{
  "cx22":  0.011,
  "cx32":  0.018,
  "cpx22": 0.020,
  "cpx32": 0.040,
  "cpx52": 0.125,
  "cpx62": 0.252,
  "ccx13": 0.018,
  "ccx23": 0.030,
  "ccx33": 0.030,
  "ccx43": 0.060,
  "ccx53": 0.090,
  "ccx63": 0.126
}'

# Print price for a given type. Empty stdout if unknown.
price_for_type() {
  local t="$1"
  printf '%s' "$PRICE_TABLE_EUR_PER_HOUR" | jq -r --arg t "$t" '.[$t] // empty'
}

# Compute cost in EUR for (type, hours).
#   calc_cost ccx33 2      -> "0.0600"
#   calc_cost ccx33 0.5    -> "0.0150"
calc_cost() {
  local t="$1" hours="$2"
  local rate
  rate="$(price_for_type "$t")"
  if [[ -z "$rate" ]]; then
    log_warn "no price entry for type '$t'"
    return 1
  fi
  awk -v rate="$rate" -v h="$hours" 'BEGIN { printf "%.4f", rate*h }'
}

# Compute cost-so-far for a running VM based on started_at.
# Prints EUR with 4 decimal places.
cost_since_start() {
  local name="$1" started_at="$2"
  local type rate hours cost
  type="$(read_cache_field "$name" type || true)"
  if [[ -z "$type" ]]; then
    if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
      # Dry-run synthetic cache always has the type; fall back to a
      # caller-provided override.
      type="${HETZNER_RUN_TYPE_OVERRIDE:-}"
    fi
    if [[ -z "$type" ]]; then
      type="$(hcloud_field_for "$name" server_type 2>/dev/null || echo "")"
    fi
  fi
  if [[ -z "$type" ]]; then
    log_warn "cost_since_start: no type for $name"
    return 1
  fi
  rate="$(price_for_type "$type")"
  if [[ -z "$rate" ]]; then
    log_warn "no price for $type"
    return 1
  fi
  if [[ -n "$started_at" && "$started_at" != "null" ]]; then
    local now_s start_s
    now_s="$(date +%s)"
    start_s="$(date -j -f '%Y-%m-%dT%H:%M:%S%z' "$started_at" +%s 2>/dev/null || \
               date -d "$started_at" +%s 2>/dev/null || echo "")"
    if [[ -n "$start_s" ]]; then
      hours=$(awk -v n="$now_s" -v s="$start_s" 'BEGIN { printf "%.6f", (n-s)/3600 }')
    else
      hours=0
    fi
  else
    hours=0
  fi
  awk -v rate="$rate" -v h="$hours" 'BEGIN { printf "%.4f", rate*h }'
}

# Best-effort lookup of a single field from hcloud server describe JSON.
hcloud_field_for() {
  local name="$1" field="$2"
  ensure_hcloud
  ensure_jq
  hcloud server describe "$name" --output json 2>/dev/null \
    | jq -r --arg f "$field" '.[$f] // empty' \
    || true
}

# --- polling utilities -----------------------------------------------------

# Poll every $1 seconds, up to $2 seconds, until $3 (a shell command) exits 0.
# Additional positional args (4+) are passed to the polled command via "$@".
# Returns 0 on success, 1 on timeout.
wait_until() {
  local interval="$1" timeout="$2" cmd="$3"
  shift 3
  local elapsed=0
  while (( elapsed <= timeout )); do
    if eval "$cmd" "$@" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$interval"
    elapsed=$(( elapsed + interval ))
  done
  return 1
}

# --- formatting ------------------------------------------------------------

format_eur() {
  awk -v x="$1" 'BEGIN { printf "€%.3f", x }'
}

# Seconds -> "Hh Mm"
format_uptime() {
  local s="$1"
  printf '%dh %02dm\n' $((s/3600)) $(((s%3600)/60))
}

# ISO-8601 now (UTC) for started_at defaults.
iso_now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

# Sanity check that a string looks like a valid Hetzner server name.
validate_name() {
  local name="$1"
  [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$ ]] || \
    die "invalid server name: $name (must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,62}\$)"
}
