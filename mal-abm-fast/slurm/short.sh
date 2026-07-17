#!/usr/bin/env bash
# short.sh — M-perf F1.a SLURM template for FT3 ilk.
#
# Single-node, 64 cores, 6h wall, module loads for Intel oneAPI 2021.3 +
# impi 2021.3 + gdal 3.7.0. Runs 100 rollouts of mal_abm_fast in
# embarrassingly-parallel OpenMP mode (F2). For F1.a (scaffold only) the
# binary just prints its version + a PRNG smoke value; the same script is
# used to verify the toolchain on FT3.
#
# Usage:
#   sbatch mal-abm-fast/slurm/short.sh
#   MONTH=6 YEAR=2024 N_ROLLOUTS=10 sbatch mal-abm-fast/slurm/short.sh
#
# SLURM output: $PROJECT_ROOT/<jobname>-<jobid>.{o,e}  (default SLURM
# cwd-relative naming; the %x/%j pattern is expanded by SLURM at submit
# time, not by this script). To get runs/logs/ semantics, set
# --output=runs/logs/%x-%j.o and `mkdir -p runs/logs` below.

set -euo pipefail

# --- CESGA module loads ------------------------------------------------------
module purge
module load cesga/system          # base env with miniconda
module load intel/2021.3.0        # icx / icpc / ifx
module load impi/2021.3.0         # Intel MPI (F4)
module load gdal/3.7.0            # COG + gpkg reader

# --- Repo + venv on $STORE ---------------------------------------------------
export PROJECT_ROOT="${PROJECT_ROOT:-$STORE/MalariaSentinel}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$STORE/MalariaSentinel/.venv}"

cd "$PROJECT_ROOT"

# --- OpenMP binding for FT3 ilk ---------------------------------------------
# 64 cores on a single ilk node (2x Ice Lake 8352Y, 32 cores per socket).
# close + cores keeps the OS scheduler from migrating threads across sockets
# (NUMA-friendly).
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-64}"
export OMP_PROC_BIND=close
export OMP_PLACES=cores

# --- Parameters (override via --export= or env on the sbatch line) -----------
MONTH="${MONTH:-6}"
YEAR="${YEAR:-2024}"
N_ROLLOUTS="${N_ROLLOUTS:-100}"
SEED_BASE="${SEED_BASE:-1}"
AOI="${AOI:-ghana}"

ENV_TIF="${PROJECT_ROOT}/data/runs/${AOI}/m2/${AOI}_regional_${YEAR}_$(printf '%02d' "$MONTH")_env.tif"
HAB_GPKG="${PROJECT_ROOT}/data/runs/${AOI}/m2/${AOI}_regional_${YEAR}_$(printf '%02d' "$MONTH")_habitat_patches.gpkg"
OUT_DIR="${PROJECT_ROOT}/runs/m-perf/${AOI}_${YEAR}_$(printf '%02d' "$MONTH")"

mkdir -p "$OUT_DIR"

# --- Build (one-time per node) -----------------------------------------------
# F1.a: build with vcpkg + CMake. Once the binary is cached on $LUSTRE,
# the build step is a no-op (incremental).
if [[ ! -x "$PROJECT_ROOT/mal-abm-fast/build/mal_abm_fast" ]]; then
  echo "[short.sh] building mal_abm_fast …"
  cmake -S "$PROJECT_ROOT/mal-abm-fast" -B "$PROJECT_ROOT/mal-abm-fast/build" \
        -DCMAKE_BUILD_TYPE=Release
  cmake --build "$PROJECT_ROOT/mal-abm-fast/build" -j
fi

# --- Run --------------------------------------------------------------------
srun "$PROJECT_ROOT/mal-abm-fast/build/mal_abm_fast" run \
    --aoi "$AOI" \
    --env "$ENV_TIF" \
    --habitat "$HAB_GPKG" \
    --output "$OUT_DIR/state.tif" \
    --days 365 \
    --n-rollouts "$N_ROLLOUTS" \
    --year "$YEAR" \
    --month "$MONTH" \
    --seed "$SEED_BASE"

echo "[short.sh] done."
