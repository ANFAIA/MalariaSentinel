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

# F1.a scaffold smoke; F2/F3 will replace with the full ABM loop.
"$PROJECT_ROOT/mal-abm-fast/build/mal_abm_fast" --version

echo "[long.sh] done. (F1.a: scaffold smoke; F2/F3 will run the ABM.)"
