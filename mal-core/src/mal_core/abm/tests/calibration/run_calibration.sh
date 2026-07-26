#!/usr/bin/env bash
set -euo pipefail

echo "=================================================================="
echo "STEP 1: Fast-tier pytest"
echo "=================================================================="
echo ""
cd /Users/davidflorezmazuera/Downloads/MalariaSentinel/mal-core/src/mal_core/abm/tests/calibration

CALIBRATION_TIER=full MAL_SEED=42 MAL_DAYS=30 MAL_N_ROLLOUTS=1 \
  uv run pytest -v --tb=short 2>&1 || true

echo ""
echo "=================================================================="
echo "STEP 2: Check data files under data/runs/ghana/"
echo "=================================================================="
echo ""
echo "--- Contents of data/runs/ ---"
ls -la /Users/davidflorezmazuera/Downloads/MalariaSentinel/data/runs/ 2>&1 || echo "(data/runs/ not found)"
echo ""
echo "--- Contents of data/ghana/ ---"
ls -la /Users/davidflorezmazuera/Downloads/MalariaSentinel/data/ghana/ 2>&1 || echo "(data/ghana/ not found)"
echo ""

echo "=================================================================="
echo "STEP 3: Test scorer infrastructure (score_run)"
echo "=================================================================="
echo ""
MAL_SEED=42 MAL_DAYS=30 MAL_N_ROLLOUTS=1 \
  uv run python -m scorers.score --run-dir /tmp/test_run --experiment baseline 2>&1 || true

echo ""
echo "=================================================================="
echo "STEP 4: Run unit tests (no integration fixtures needed)"
echo "=================================================================="
echo ""
uv run pytest tests/ -v --tb=short 2>&1 || true

echo ""
echo "=================================================================="
echo "DONE"
echo "=================================================================="
