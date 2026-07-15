#!/usr/bin/env bash
# CESGA FinisTerrae III — configuration for MalariaSentinel ABM runs
# Source this file; do not execute directly.
#
# The repo lives on LUSTRE-backed home at:
#   /mnt/lustre/scratch/nlsas/home/ulc/cursos/curso309/MalariaSentinel
# Data and runs are within the repo tree — no separate STORE/LUSTRE needed.

# --- Paths ------------------------------------------------------------------
CESGA_USER="${CESGA_USER:-$USER}"
# Detect project root from this script's location (scripts/cesga-run/ → repo root)
_CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$_CONFIG_DIR/../../.." && pwd)"

# Data already lives in the repo
DATA_DIR="${DATA_DIR:-$PROJECT_ROOT/data/runs/ghana/m2}"
RUNS_DIR="${RUNS_DIR:-$PROJECT_ROOT/runs}"
LOGS_DIR="${LOGS_DIR:-$PROJECT_ROOT/runs/logs}"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv}"

# --- SLURM resource defaults ------------------------------------------------
SLURM_PARTITION="medium"         # 3-day max
SLURM_CORES=32                  # of 64 available on ILK nodes
SLURM_MEM="64G"                 # of 256GB available
SLURM_TIME="2-23:59:00"         # Just under 3-day limit

# --- ABM parameters ---------------------------------------------------------
ABM_AOI="ghana"
ABM_SEED_START=1
ABM_DAYS_PER_MONTH=30
ABM_START_YEAR=2024
ABM_START_MONTH=1
ABM_NUM_MONTHS=24               # 2 years

# --- uv cache (must be outside $HOME — quota is only 10GB) -------------------
UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJECT_ROOT/.uv-cache}"

# --- Derived (do not edit below) -------------------------------------------
export CESGA_USER PROJECT_ROOT DATA_DIR RUNS_DIR LOGS_DIR VENV_DIR UV_CACHE_DIR
export SLURM_PARTITION SLURM_CORES SLURM_MEM SLURM_TIME
export ABM_AOI ABM_SEED_START ABM_DAYS_PER_MONTH ABM_START_YEAR ABM_START_MONTH ABM_NUM_MONTHS
