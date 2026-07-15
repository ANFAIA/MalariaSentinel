#!/usr/bin/env bash
#SBATCH -J malaria-abm
#SBATCH -p long
#SBATCH -c 32
#SBATCH --mem=64G
#SBATCH -t 6-00:00:00
#SBATCH -o /mnt/lustre/scratch/%u/malaria-sentinel/logs/%x-%j.o
#SBATCH -e /mnt/lustre/scratch/%u/malaria-sentinel/logs/%x-%j.e

# run_abm.sh — SLURM batch script for MalariaSentinel ABM on CESGA
# Runs 24 months (2 years) sequentially on an ILK node.
#
# Usage (interactive or from manage_jobs.sh):
#   sbatch run_abm.sh
#   sbatch --export=ABM_SEED=5,ABM_START_MONTH=7 run_abm.sh

set -euo pipefail

# --- Source config -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=cesga_config.sh
source "$SCRIPT_DIR/cesga_config.sh"

# Override defaults via --export=VAR=VAL on sbatch command line
YEAR="${ABM_START_YEAR:-2024}"
MONTH="${ABM_START_MONTH:-1}"
NUM_MONTHS="${ABM_NUM_MONTHS:-24}"
SEED="${ABM_SEED:-1}"
DAYS="${ABM_DAYS_PER_MONTH:-30}"
AOI="${ABM_AOI:-ghana}"

# --- Environment tuning for numpy/polars/mkl --------------------------------
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-32}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-32}"
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK:-32}"

# --- Directories -------------------------------------------------------------
export PATH="$HOME/.local/bin:$PATH"
DATA_DIR="${DATA_DIR:-${LUSTRE}/malaria-sentinel/data}"
RUNS_DIR="${RUNS_DIR:-${STORE}/malaria-sentinel/runs}"
LOGS_DIR="${LOGS_DIR:-${STORE}/malaria-sentinel/logs}"
VENV_DIR="${VENV_DIR:-${STORE}/.venv}"

mkdir -p "$RUNS_DIR" "$LOGS_DIR"

# --- Activate venv -----------------------------------------------------------
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
else
  echo "ERROR: venv not found at $VENV_DIR — run setup_env.sh first" >&2
  exit 1
fi

# --- Timing ------------------------------------------------------------------
JOB_START=$(date +%s)
echo "=== MalariaSentinel ABM ==="
echo "Job ID:     ${SLURM_JOB_ID:-local}"
echo "Node:       ${SLURM_NODELIST:-$(hostname)}"
echo "CPUs:       ${SLURM_CPUS_PER_TASK:-32}"
echo "Memory:     ${SLURM_MEM_PER_NODE:-64G}"
echo "AOI:        $AOI"
echo "Period:     $YEAR-$(printf '%02d' $MONTH) to $(printf '%04d' $(( YEAR + (MONTH + NUM_MONTHS - 2) / 12 )))-$(printf '%02d' $(( (MONTH + NUM_MONTHS - 2) % 12 + 1 )))"
echo "Seed:       $SEED"
echo "Days/month: $DAYS"
echo "Data dir:   $DATA_DIR"
echo "Runs dir:   $RUNS_DIR"
echo "==========================="
echo ""

MONTHS_RUN=0
MONTHS_FAILED=0

for (( i=0; i<NUM_MONTHS; i++ )); do
  M=$(( MONTH + i ))
  Y=$(( YEAR + (M - 1) / 12 ))
  M=$(( (M - 1) % 12 + 1 ))

  MM=$(printf '%04d_%02d' "$Y" "$M")
  ENV_TIF="${DATA_DIR}/${AOI}_regional_${MM}_env.tif"
  HAB_GPKG="${DATA_DIR}/${AOI}_regional_${MM}_habitat_patches.gpkg"
  OUT_TIF="${RUNS_DIR}/${AOI}_regional_${MM}_seed$(printf '%04d' "$SEED").tif"

  echo "--- [$(( i + 1 ))/$NUM_MONTHS] $Y-$(printf '%02d' "$M") seed=$SEED ---"

  if [[ ! -f "$ENV_TIF" ]]; then
    echo "  ERROR: env COG missing: $ENV_TIF"
    MONTHS_FAILED=$((MONTHS_FAILED + 1))
    continue
  fi
  if [[ ! -f "$HAB_GPKG" ]]; then
    echo "  ERROR: habitat gpkg missing: $HAB_GPKG"
    MONTHS_FAILED=$((MONTHS_FAILED + 1))
    continue
  fi

  MONTH_START=$(date +%s)

  python -m mal_ghana_sim.abm.run \
    --aoi "$AOI" \
    --year "$Y" \
    --month "$M" \
    --env "$ENV_TIF" \
    --habitat "$HAB_GPKG" \
    --output "$OUT_TIF" \
    --seed "$SEED" \
    --days "$DAYS"

  MONTH_END=$(date +%s)
  ELAPSED=$(( MONTH_END - MONTH_START ))
  echo "  Done in $(( ELAPSED / 60 ))m $(( ELAPSED % 60 ))s -> $OUT_TIF"
  echo ""

  MONTHS_RUN=$((MONTHS_RUN + 1))
done

# --- Final summary -----------------------------------------------------------
JOB_END=$(date +%s)
TOTAL_ELAPSED=$(( JOB_END - JOB_START ))

echo "=== Run complete ==="
echo "Months run:    $MONTHS_RUN / $NUM_MONTHS"
echo "Months failed: $MONTHS_FAILED"
echo "Total time:    $(( TOTAL_ELAPSED / 3600 ))h $(( (TOTAL_ELAPSED % 3600) / 60 ))m $(( TOTAL_ELAPSED % 60 ))s"
echo "Outputs:       $RUNS_DIR/${AOI}_regional_*_seed$(printf '%04d' "$SEED").tif"
echo "===================="

if [[ "$MONTHS_FAILED" -gt 0 ]]; then
  exit 1
fi
