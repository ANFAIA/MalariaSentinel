#!/usr/bin/env bash
# MalariaSentinel end-to-end pipeline — reproducible download→ingest→abm run.
#
# Invoked explicitly, NOT on container start:
#   docker run --rm -it \
#     -v "$PWD/data:/app/data" \
#     -v "$PWD/runs:/app/runs" \
#     malariasim:local pipeline
#
# Stages (in order):
#   1. download  — only runs when the AOI manifest is incomplete (i.e. data
#                  has not been downloaded yet). Skips auth-required sources
#                  (era5/modis/smap) unless credentials are provided.
#   2. ingest    — build env tensor + habitat patches + hosts + mobility.
#   3. abm       — run the C++ agent-based model.
#
# All paths default to /app/data and /app/runs (bind-mounted by compose).
# Override via env: AOI, YEAR, MONTH, DAYS, SEED, DATA_DIR, RUNS_DIR,
# and FORCE_DOWNLOAD=1 to always re-run the download stage.
set -euo pipefail

AOI="${AOI:-ghana}"
YEAR="${YEAR:-2024}"
MONTH="${MONTH:-6}"
DAYS="${DAYS:-30}"
SEED="${SEED:-1}"
DATA_DIR="${DATA_DIR:-/app/data/$AOI}"
RUNS_DIR="${RUNS_DIR:-/app/runs/abm}"
DATA_ROOT="$(dirname "$DATA_DIR")"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die()  { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

command -v malariasim >/dev/null || die "malariasim not found on PATH"

mkdir -p "$DATA_DIR" "$RUNS_DIR"

# --- Stage 1: download (only when manifest incomplete) ------------------------
log "Stage 1/3: download --aoi $AOI (data root: $DATA_ROOT)"
if [ "${FORCE_DOWNLOAD:-0}" = "1" ]; then
    echo "FORCE_DOWNLOAD=1 — running download stage."
    malariasim download --aoi "$AOI" --output-dir "$DATA_DIR" || true
else
    python - "$AOI" "$DATA_ROOT" <<'PY' || true
import sys
from pathlib import Path
from mal_core.download.manifest import validate_completeness

aoi, data_root = sys.argv[1], Path(sys.argv[2])
missing = validate_completeness(aoi, data_root=data_root)
if missing:
    print(f"manifest incomplete ({len(missing)} missing files) — download needed")
    sys.exit(1)
print("manifest complete — skipping download")
PY
    if [ $? -ne 0 ]; then
        echo "Downloading datasets for $AOI ..."
        malariasim download --aoi "$AOI" --output-dir "$DATA_DIR" || true
    fi
fi

# --- Stage 2: ingest ---------------------------------------------------------
log "Stage 2/3: ingest --aoi $AOI --year $YEAR --month $MONTH"
malariasim ingest --aoi "$AOI" --year "$YEAR" --month "$MONTH" \
    --output-dir "$DATA_DIR" --data-dir "$DATA_DIR"

# --- Stage 3: ABM ------------------------------------------------------------
log "Stage 3/3: abm --aoi $AOI --year $YEAR --month $MONTH --days $DAYS --seed $SEED"
malariasim abm --aoi "$AOI" --year "$YEAR" --month "$MONTH" \
    --days "$DAYS" --seed "$SEED" \
    --data-root "$DATA_ROOT" \
    --output-dir "$RUNS_DIR"

log "Pipeline complete."
echo "ABM outputs in $RUNS_DIR:"
ls -lh "$RUNS_DIR" | tail -n +1