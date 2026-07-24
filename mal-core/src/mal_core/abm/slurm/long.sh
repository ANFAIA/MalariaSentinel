#!/usr/bin/env bash
# long.sh — M-perf F1.a SLURM template for FT3 ilk, 7d wall.
# Use this for multi-month rollouts (e.g. 100 rollouts × 24 months for U-Net
# training data). F1.a scaffold only — the ABM body is F2/F3.
#
# Usage:
#   sbatch mal-abm-fast/slurm/long.sh
#   NUM_MONTHS=24 N_ROLLOUTS=100 sbatch mal-abm-fast/slurm/long.sh

#SBATCH --job-name=mal-abm-fast-long
#SBATCH --partition=long
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=128G
#SBATCH --time=7-00:00:00
#SBATCH --output=%x-%j.o
#SBATCH --error=%x-%j.e

set -euo pipefail

module purge
module load cesga/system
module load intel/2021.3.0
module load impi/2021.3.0
module load gdal/3.7.0

export PROJECT_ROOT="${PROJECT_ROOT:-$STORE/MalariaSentinel}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$STORE/MalariaSentinel/.venv}"

cd "$PROJECT_ROOT"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-64}"
export OMP_PROC_BIND=close
export OMP_PLACES=cores

NUM_MONTHS="${NUM_MONTHS:-24}"
N_ROLLOUTS="${N_ROLLOUTS:-100}"
AOI="${AOI:-ghana}"

OUT_DIR="${PROJECT_ROOT}/runs/m-perf/${AOI}_long_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"

if [[ ! -x "$PROJECT_ROOT/mal-abm-fast/build/mal_abm_fast" ]]; then
  echo "[long.sh] building mal_abm_fast …"
  cmake -S "$PROJECT_ROOT/mal-abm-fast" -B "$PROJECT_ROOT/mal-abm-fast/build" \
        -DCMAKE_BUILD_TYPE=Release
  cmake --build "$PROJECT_ROOT/mal-abm-fast/build" -j
fi

MONTH="${MONTH:-6}"
YEAR="${YEAR:-2024}"
SEED_BASE="${SEED_BASE:-1}"

ENV_TIF="${PROJECT_ROOT}/data/runs/${AOI}/m2/${AOI}_regional_${YEAR}_$(printf '%02d' "$MONTH")_env.tif"
HAB_GPKG="${PROJECT_ROOT}/data/runs/${AOI}/m2/${AOI}_regional_${YEAR}_$(printf '%02d' "$MONTH")_habitat_patches.gpkg"

# F2: run the full ABM loop with OpenMP parallelism.
DAYS_PER_MONTH=30
TOTAL_DAYS=$((NUM_MONTHS * DAYS_PER_MONTH))

srun "$PROJECT_ROOT/mal-abm-fast/build/mal_abm_fast" run \
    --aoi "$AOI" \
    --env "$ENV_TIF" \
    --habitat "$HAB_GPKG" \
    --output "$OUT_DIR/state.tif" \
    --days "$TOTAL_DAYS" \
    --n-rollouts "$N_ROLLOUTS" \
    --year "$YEAR" \
    --month "$MONTH" \
    --seed "$SEED_BASE"

echo "[long.sh] done."
