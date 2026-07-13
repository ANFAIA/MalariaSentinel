#!/usr/bin/env bash
# hetzner-run — offline test suite. No hcloud, no SSH, no network.
#
# Exits 0 on success, non-zero on first failure. The whole suite is wrapped
# in a per-test timeout (HETZNER_RUN_TEST_TIMEOUT, default 20s) so a stuck
# subcommand can never hang the suite.

set -uo pipefail

PKG_DIR="$(cd -P "$(dirname "$0")/.." && pwd)"
MAIN="$PKG_DIR/hetzner-run"
TEST_TIMEOUT="${HETZNER_RUN_TEST_TIMEOUT:-20}"

pass=0
fail=0

ok()   { printf '  \033[32mOK\033[0m   %s\n' "$*"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$*"; fail=$((fail+1)); }
hdr()  { printf '\n=== %s ===\n' "$*"; }

# Run a command in a clean isolated cache dir so we don't touch the real
# ~/.cache/hetzner-run.
TEMP_CACHE="$(mktemp -d -t hetzner-run-test-XXXXXX)"
export HETZNER_RUN_CACHE_DIR="$TEMP_CACHE"
trap 'rm -rf "$TEMP_CACHE"' EXIT

# run_with_timeout <label> <cmd...>
#   Runs cmd; if it does not exit within TEST_TIMEOUT seconds, kills it and
#   reports a failure. Returns the captured exit code via $?.
run_with_timeout() {
  local label="$1"; shift
  local out_file err_file rc_file pid
  out_file="$(mktemp -t hr-out-XXXXXX)"
  err_file="$(mktemp -t hr-err-XXXXXX)"
  rc_file="$(mktemp -t hr-rc-XXXXXX)"

  (
    # Redirect inside the subshell so the timeout'd process can't inherit
    # the test's stdin/stdout.
    "$@" >"$out_file" 2>"$err_file"
    echo $? >"$rc_file"
  ) &
  pid=$!

  local elapsed=0
  while (( elapsed < TEST_TIMEOUT )); do
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 1
    elapsed=$(( elapsed + 1 ))
  done

  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
    bad "$label: TIMED OUT after ${TEST_TIMEOUT}s"
    rm -f "$out_file" "$err_file" "$rc_file"
    return 124
  fi
  wait "$pid" 2>/dev/null || true

  LAST_OUT="$(cat "$out_file")"
  LAST_ERR="$(cat "$err_file")"
  LAST_RC="$(cat "$rc_file")"
  rm -f "$out_file" "$err_file" "$rc_file"
  return 0
}

assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  if printf '%s' "$haystack" | grep -qF -- "$needle"; then
    ok "$label (contains: $needle)"
  else
    bad "$label (missing: $needle)"
    printf '  out:\n' >&2
    printf '%s\n' "$haystack" | sed 's/^/    | /' >&2
  fi
}

LAST_OUT=""
LAST_ERR=""
LAST_RC=""

# 1. Syntax check every bash file in the package.
hdr "syntax check"
while IFS= read -r -d '' f; do
  if bash -n "$f"; then
    ok "bash -n $f"
  else
    bad "bash -n $f"
  fi
done < <(find "$PKG_DIR" -type f \( -name "*.sh" -o -name "hetzner-run" \) -print0)

# 2. Cloud-init YAML is parseable.
hdr "cloud-init yaml"
if command -v python3 >/dev/null 2>&1; then
  if python3 -c "import yaml; yaml.safe_load(open('$PKG_DIR/cloud-init.yaml'))" 2>/dev/null; then
    ok "cloud-init.yaml parses as YAML"
  elif python3 -c "import yaml" 2>/dev/null; then
    bad "cloud-init.yaml did not parse"
  else
    # PyYAML not available — fall back to a structural check that the
    # top-level directive key looks reasonable.
    if head -1 "$PKG_DIR/cloud-init.yaml" | grep -q '^#cloud-config$'; then
      ok "cloud-init.yaml starts with #cloud-config (PyYAML not installed; structural check only)"
    else
      bad "cloud-init.yaml is missing the #cloud-config header"
    fi
  fi
else
  bad "python3 not available; cannot validate cloud-init.yaml"
fi

# 3. --help smoke test for main and every subcommand.
hdr "help smoke"
for arg in --help -h help; do
  run_with_timeout "main --help ($arg)" "$MAIN" "$arg"
  if [[ "$LAST_RC" == "0" ]]; then
    assert_contains "main --help ($arg)" "hetzner-run" "$LAST_OUT"
  else
    bad "main --help ($arg) exit $LAST_RC"
  fi
done

for sub in start stop destroy status exec push pull sim-run train cost; do
  run_with_timeout "$sub --help" "$MAIN" "$sub" --help
  if [[ "$LAST_RC" == "0" ]]; then
    assert_contains "$sub --help" "hetzner-run $sub" "$LAST_OUT"
  else
    bad "$sub --help exit $LAST_RC"
  fi
done

# 4. --dry-run start.
hdr "dry-run start"
run_with_timeout "--dry-run start" "$MAIN" --dry-run start --type ccx33 --name dryrun-test
if [[ "$LAST_RC" == "0" ]]; then
  ok "--dry-run start exit 0"
else
  bad "--dry-run start exit $LAST_RC"
fi
assert_contains "--dry-run start" "hcloud server create" "$LAST_ERR"
assert_contains "--dry-run start" "ccx33" "$LAST_ERR"
assert_contains "--dry-run start" "dryrun-test" "$LAST_ERR"
assert_contains "--dry-run start" "ubuntu-24.04" "$LAST_ERR"
if printf '%s' "$LAST_OUT" | grep -qE 'ERROR|invalid token|unauthorized'; then
  bad "--dry-run start should not have made a real API call"
else
  ok "--dry-run start made no real API call"
fi

# 5. --dry-run sim-run.
hdr "dry-run sim-run"
# Pretend the default repo + data paths exist for the dry-run validation.
TMP_REPO="$(mktemp -d -t hr-repo-XXXXXX)"
TMP_DATA="$(mktemp -d -t hr-data-XXXXXX)"
run_with_timeout "--dry-run sim-run" "$MAIN" --dry-run sim-run \
  --name dryrun-sim --repo "$TMP_REPO" --data "$TMP_DATA"
if [[ "$LAST_RC" == "0" ]]; then
  ok "--dry-run sim-run exit 0"
else
  bad "--dry-run sim-run exit $LAST_RC: $LAST_ERR"
fi
assert_contains "--dry-run sim-run" "sim-run plan" "$LAST_ERR"
assert_contains "--dry-run sim-run" "/work/code/" "$LAST_ERR"
assert_contains "--dry-run sim-run" "uv sync" "$LAST_ERR"
assert_contains "--dry-run sim-run" "scripts/03_simulate.py" "$LAST_ERR"
rm -rf "$TMP_REPO" "$TMP_DATA"

# 6. Cost calculator.
hdr "cost calculator"
run_with_timeout "cost ccx33 2h" "$MAIN" cost --type ccx33 --hours 2
if [[ "$LAST_RC" == "0" ]]; then
  ok "cost --type ccx33 --hours 2 exit 0"
else
  bad "cost --type ccx33 --hours 2 exit $LAST_RC"
fi
assert_contains "cost ccx33×2" "€0.060" "$LAST_OUT"

run_with_timeout "cost ccx33 1h" "$MAIN" cost --type ccx33 --hours 1
assert_contains "cost ccx33×1" "€0.030" "$LAST_OUT"

run_with_timeout "cost ccx63 1h" "$MAIN" cost --type ccx63 --hours 1
assert_contains "cost ccx63×1" "€0.126" "$LAST_OUT"

run_with_timeout "cost cx22 1h" "$MAIN" cost --type cx22 --hours 1
assert_contains "cost cx22×1" "€0.011" "$LAST_OUT"

# 7. cost --list.
hdr "cost --list"
run_with_timeout "cost --list" "$MAIN" cost --list
if [[ "$LAST_RC" == "0" ]]; then
  ok "cost --list exit 0"
else
  bad "cost --list exit $LAST_RC"
fi
for t in ccx33 cpx62 cx22 cx32 ccx43 ccx63; do
  assert_contains "cost --list includes $t" "$t" "$LAST_OUT"
done

# 8. Bad-name validation.
hdr "input validation"
run_with_timeout "start rejects bad name" "$MAIN" start --name 'bad name with spaces'
if [[ "$LAST_RC" != "0" ]]; then
  ok "start rejects invalid name (exit $LAST_RC)"
else
  bad "start should reject invalid name (got exit 0)"
fi

# 9. Subcommand routing for an unknown subcommand.
hdr "unknown subcommand"
run_with_timeout "unknown subcommand" "$MAIN" bogus-subcommand
if [[ "$LAST_RC" != "0" ]]; then
  ok "unknown subcommand exits non-zero"
  assert_contains "unknown subcommand message" "unknown subcommand" "$LAST_ERR"
else
  bad "unknown subcommand should exit non-zero"
fi

# 10. Cache writes during dry-run start.
hdr "dry-run start writes a cache entry"
run_with_timeout "dry-run start writes cache" "$MAIN" --dry-run start --name ms-cache-check
if [[ -f "$TEMP_CACHE/ms-cache-check.json" ]]; then
  ok "dry-run start wrote cache file"
  if jq -e '.ip' "$TEMP_CACHE/ms-cache-check.json" >/dev/null 2>&1; then
    ok "cache file has an ip field"
  else
    bad "cache file missing ip field"
  fi
else
  bad "dry-run start did not write a cache file (stderr: $LAST_ERR)"
fi

# 11. Dry-run stop / destroy / exec / push / pull are also dry.
hdr "dry-run subcommands"
# These all need a name. Use the cache we just wrote so resolve_ip returns
# 127.0.0.1 in dry-run mode.
run_with_timeout "--dry-run stop" "$MAIN" --dry-run stop ms-cache-check
if [[ "$LAST_RC" == "0" ]]; then ok "--dry-run stop exit 0"; else bad "--dry-run stop exit $LAST_RC"; fi
assert_contains "--dry-run stop prints dry-run marker" "dry-run" "$LAST_ERR"

run_with_timeout "--dry-run destroy" "$MAIN" --dry-run destroy ms-cache-check
if [[ "$LAST_RC" == "0" ]]; then ok "--dry-run destroy exit 0"; else bad "--dry-run destroy exit $LAST_RC"; fi
assert_contains "--dry-run destroy prints dry-run marker" "dry-run" "$LAST_ERR"

run_with_timeout "--dry-run exec" "$MAIN" --dry-run exec ms-cache-check ls
if [[ "$LAST_RC" == "0" ]]; then ok "--dry-run exec exit 0"; else bad "--dry-run exec exit $LAST_RC"; fi
assert_contains "--dry-run exec prints dry-run marker" "dry-run" "$LAST_ERR"

run_with_timeout "--dry-run push" "$MAIN" --dry-run push ms-cache-check /tmp /work
if [[ "$LAST_RC" == "0" ]]; then ok "--dry-run push exit 0"; else bad "--dry-run push exit $LAST_RC"; fi
assert_contains "--dry-run push prints dry-run marker" "dry-run" "$LAST_ERR"

run_with_timeout "--dry-run pull" "$MAIN" --dry-run pull ms-cache-check /work /tmp
if [[ "$LAST_RC" == "0" ]]; then ok "--dry-run pull exit 0"; else bad "--dry-run pull exit $LAST_RC"; fi
assert_contains "--dry-run pull prints dry-run marker" "dry-run" "$LAST_ERR"

run_with_timeout "--dry-run status" "$MAIN" --dry-run status
if [[ "$LAST_RC" == "0" ]]; then ok "--dry-run status exit 0"; else bad "--dry-run status exit $LAST_RC"; fi
assert_contains "--dry-run status prints dry-run marker" "dry-run" "$LAST_ERR"

# Summary
printf '\n--- summary ---\n'
printf '  passed: %d\n' "$pass"
printf '  failed: %d\n' "$fail"

if (( fail > 0 )); then
  exit 1
fi
exit 0
