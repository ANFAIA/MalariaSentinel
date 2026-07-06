#!/usr/bin/env bash
# tools/hitl/check-edit.sh
# Human-in-the-loop check for edits to protected files.
#
# Usage:
#   check-edit.sh <path> [<path> ...]
#
# Reads:
#   - tools/hitl/.protected            (canonical list, committed)
#   - tools/hitl/.protected-allowances (runtime per-session permissions, gitignored)
#
# Exit codes:
#   0  every path is OK to edit (non-protected, or covered by an allowance)
#   1  at least one path is protected AND not allowed — block + explain
#   2  usage error or missing config
#
# A path is "allowed" if it matches an entry in .protected-allowances via
# fnmatch (so wildcards work: tools/memory/*.sh, etc.). A path that does
# NOT match any entry in .protected is allowed by default — this file
# only restricts what .protected names, never more.
#
# Compatibility: uses bash 3.2 constructs only (no mapfile, no associative
# arrays), so it works on the macOS-shipped bash.

set -uo pipefail

# Use BASH_SOURCE (not $0) so this works whether the script is invoked
# directly or via `bash path/to/check-edit.sh ...` from the Makefile.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROTECTED="$HERE/.protected"
ALLOWANCES="$HERE/.protected-allowances"

[ -f "$PROTECTED" ] || { echo "check-edit.sh: missing $PROTECTED" >&2; exit 2; }

# --- load the protected list (one path per line, no mapfile) ---
PROTECTED_PATTERNS=""
while IFS= read -r line; do
  # skip comments and blank lines
  case "$line" in
    '' | '#'* | '//'* | '<!--'*) continue ;;
  esac
  PROTECTED_PATTERNS="${PROTECTED_PATTERNS}${line}"$'\n'
done < "$PROTECTED"

# --- load the allowances ---
ALLOWED_PATTERNS=""
if [ -f "$ALLOWANCES" ]; then
  while IFS= read -r line; do
    case "$line" in
    '' | '#'* | '//'* | '<!--'*) continue ;;
  esac
    ALLOWED_PATTERNS="${ALLOWED_PATTERNS}${line}"$'\n'
  done < "$ALLOWANCES"
fi

# --- is this path covered by an allowance? ---
_is_allowed() {
  local p="$1"
  local pat
  while IFS= read -r pat; do
    [ -z "$pat" ] && continue
    # shellcheck disable=SC2053
    [[ "$p" == $pat ]] && return 0
  done <<< "$ALLOWED_PATTERNS"
  return 1
}

# --- does this path match a protected pattern? ---
_is_protected() {
  local p="$1"
  local pat
  while IFS= read -r pat; do
    [ -z "$pat" ] && continue
    # shellcheck disable=SC2053
    [[ "$p" == $pat ]] && return 0
  done <<< "$PROTECTED_PATTERNS"
  return 1
}

[ $# -ge 1 ] || { echo "usage: check-edit.sh <path> [<path> ...]" >&2; exit 2; }

blocked=""
allowed_via_allowance=""
non_protected=""

for p in "$@"; do
  if _is_protected "$p"; then
    if _is_allowed "$p"; then
      allowed_via_allowance="${allowed_via_allowance}${p}"$'\n'
    else
      blocked="${blocked}${p}"$'\n'
    fi
  else
    non_protected="${non_protected}${p}"$'\n'
  fi
done

# --- report ---
if [ -n "$non_protected" ]; then
  echo "OK (non-protected):"
  printf '  - %s\n' $non_protected
fi

if [ -n "$allowed_via_allowance" ]; then
  echo "OK (protected, but allowed via .protected-allowances):"
  printf '  - %s\n' $allowed_via_allowance
fi

if [ -n "$blocked" ]; then
  echo "BLOCKED — protected and not allowed:" >&2
  printf '  - %s\n' $blocked >&2
  echo >&2
  echo "These files are part of the reusable project infrastructure." >&2
  echo "Per AGENTS.md, the agent MUST ask the user before editing them." >&2
  echo >&2
  echo "To grant a one-off permission for this session:" >&2
  echo "  make -f tools/hitl/Makefile protected-allow P=<path>" >&2
  echo >&2
  echo "If the user has already approved the change in chat, run that" >&2
  echo "command and then proceed. The allowance is logged to" >&2
  echo "  tools/hitl/.protected-allowances" >&2
  echo "and is gitignored (per-session state, not committed)." >&2
  exit 1
fi

exit 0
