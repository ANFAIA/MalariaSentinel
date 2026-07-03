# Terrain

SRTM DEM tiles and download scripts for all study regions.

## ⚠️ Recovery Notice

The original SRTM tiles were lost (2026-07-03). Re-download using the scripts below.

## Contents

```
terrain/
  srtm_maps/         Downloaded SRTM tiles by region (re-download with download_srtm.py)
  srtm_guf/          SRTM for Guayana Francesa (re-download with download_srtm_guf.py)
  download_srtm.py   Download SRTM for all configured regions
  download_srtm_guf.py Download SRTM for Guayana Francesa
  README.md          This file
```

## Usage

```bash
export OPENTOPO_API_KEY=<your_key>

# Download SRTM for all configured regions
uv run python download_srtm.py

# Download SRTM for Guayana Francesa
uv run python download_srtm_guf.py
```

Source: [OpenTopography](https://portal.opentopography.org/) (OT.042013.4326.1).