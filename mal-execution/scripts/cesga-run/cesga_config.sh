#!/usr/bin/env bash
# CESGA FinisTerrae III — configuration for MalariaSentinel ABM runs
# Source this file; do not execute directly.

# --- CESGA user -------------------------------------------------------------
CESGA_USER="${CESGA_USER:-$USER}"

# --- Paths ------------------------------------------------------------------
# $STORE is persistent across jobs (scratch Lustre, 30-day purge on some
# allocations).  $LUSTRE is the fast parallel filesystem for I/O-heavy work.
STORE="${STORE:-/mnt/lustre/scratch/${CESGA_USER}}"
LUSTRE="${LUSTRE:-/mnt/lustre/scratch/${CESGA_USER}}"

# Project root on CESGA (after rsync / git clone)
PROJECT_ROOT="${PROJECT_ROOT:-${LUSTRE}/MalariaSentinel}"

# Data lives on LUSTRE for fast I/O; results persist on $STORE.
DATA_DIR="${LUSTRE}/malaria-sentinel/data"
RUNS_DIR="${STORE}/malaria-sentinel/runs"
LOGS_DIR="${STORE}/malaria-sentinel/logs"
VENV_DIR="${STORE}/.venv"

# --- SLURM resource defaults ------------------------------------------------
SLURM_PARTITION="long"          # 7-day max
SLURM_CORES=32                  # of 64 available on ILK nodes
SLURM_MEM="64G"                 # of 256GB available
SLURM_TIME="6-00:00:00"         # 6 days (safe under 7-day limit)

# --- ABM parameters ---------------------------------------------------------
ABM_AOI="ghana"
ABM_SEED_START=1
ABM_DAYS_PER_MONTH=30
ABM_START_YEAR=2024
ABM_START_MONTH=1
ABM_NUM_MONTHS=24               # 2 years

# --- Derived (do not edit below) -------------------------------------------
export CESGA_USER STORE LUSTRE PROJECT_ROOT DATA_DIR RUNS_DIR LOGS_DIR VENV_DIR
export SLURM_PARTITION SLURM_CORES SLURM_MEM SLURM_TIME
export ABM_AOI ABM_SEED_START ABM_DAYS_PER_MONTH ABM_START_YEAR ABM_START_MONTH ABM_NUM_MONTHS
