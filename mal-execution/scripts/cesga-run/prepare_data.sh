#!/usr/bin/env bash
# prepare_data.sh — build env COGs + habitat patches for ABM months
# Run on a login node (data loaders hit Planetary Computer / GCS).
#
# On CESGA, data already exists at $DATA_DIR (repo is on LUSTRE).
# This script checks for existing files and skips them by default.
# Use --force to rebuild even if files exist.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=cesga_config.sh
source "$SCRIPT_DIR/cesga_config.sh"

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

# --- Usage -------------------------------------------------------------------
usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Prepare env COGs + habitat patches for the ABM on CESGA.
Data already exists in the repo on LUSTRE — this script validates
and optionally rebuilds.

Options:
  --year  START_YEAR   First year  (default: $ABM_START_YEAR)
  --month START_MONTH  First month (default: $ABM_START_MONTH)
  --num   NUM_MONTHS   Total months (default: $ABM_NUM_MONTHS)
  --force              Rebuild even if files already exist
  --dry-run            Print commands without executing
  -h, --help           Show this help
EOF
  exit 0
}

YEAR=$ABM_START_YEAR
MONTH=$ABM_START_MONTH
NUM=$ABM_NUM_MONTHS
FORCE=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --year)   YEAR="$2";  shift 2;;
    --month)  MONTH="$2"; shift 2;;
    --num)    NUM="$2";   shift 2;;
    --force)  FORCE=1;    shift;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) usage;;
    *) echo "Unknown option: $1"; usage;;
  esac
done

# --- Preflight ---------------------------------------------------------------
mkdir -p "$DATA_DIR" "$LOGS_DIR"

export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv &>/dev/null; then
  log "ERROR: uv not found. Run setup_env.sh first."
  exit 1
fi

# --- Build loop --------------------------------------------------------------
TOTAL=0
BUILT=0
SKIPPED=0
FAILED=0

for (( i=0; i<NUM; i++ )); do
  M=$(( MONTH + i ))
  Y=$(( YEAR + (M - 1) / 12 ))
  M=$(( (M - 1) % 12 + 1 ))

  TOTAL=$((TOTAL + 1))
  ENV_TIF="${DATA_DIR}/${ABM_AOI}_regional_$(printf '%04d_%02d' "$Y" "$M")_env.tif"
  HAB_GPKG="${DATA_DIR}/${ABM_AOI}_regional_$(printf '%04d_%02d' "$Y" "$M")_habitat_patches.gpkg"

  if [[ "$FORCE" -eq 0 && -f "$ENV_TIF" && -f "$HAB_GPKG" ]]; then
    log "[SKIP] $Y-$(printf '%02d' "$M") — files exist"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  if [[ "$FORCE" -eq 1 && -f "$ENV_TIF" && -f "$HAB_GPKG" ]]; then
    log "[REBUILD] $Y-$(printf '%02d' "$M") — --force set, rebuilding"
  else
    log "[BUILD] $Y-$(printf '%02d' "$M") — missing files, building …"
  fi

  CMD=(
    uv run python -m mal_ghana_sim.scripts.build_env
    --aoi "$ABM_AOI"
    --year "$Y"
    --month "$M"
    --output-dir "$DATA_DIR"
  )

  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "  dry-run: ${CMD[*]}"
    continue
  fi

  if "${CMD[@]}" 2>&1 | tee -a "$LOGS_DIR/build_env_${Y}_${M}.log"; then
    if [[ -f "$ENV_TIF" && -f "$HAB_GPKG" ]]; then
      log "[OK]   $Y-$(printf '%02d' "$M")"
      BUILT=$((BUILT + 1))
    else
      log "[FAIL] $Y-$(printf '%02d' "$M") — output files missing"
      FAILED=$((FAILED + 1))
    fi
  else
    log "[FAIL] $Y-$(printf '%02d' "$M") — build_env exited non-zero"
    FAILED=$((FAILED + 1))
  fi
done

# --- Summary -----------------------------------------------------------------
log "─────────────────────────────────────"
log "Prepared $TOTAL months: $BUILT built, $SKIPPED skipped, $FAILED failed"
log "─────────────────────────────────────"

# --- Disk usage --------------------------------------------------------------
log "Disk usage in $DATA_DIR:"
du -sh "$DATA_DIR" 2>/dev/null || true

exit "$FAILED"
