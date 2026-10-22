#!/usr/bin/env python3
"""Regenerate the committed tiny golden fixtures (task-06 decision 1).

The golden used to require ``data/accra-coastal-test`` (gitignored), so a
fresh clone failed two ctest cases. This script builds a self-contained
8x8-cell AOI under ``tests/fixtures/`` and runs the real engine to freeze
its behaviour in ``tests/golden/``.

Run from the repo root after building the engine:

    uv run python mal-core/src/mal_core/abm/tests/fixtures/make_golden_fixtures.py

The generated files ARE committed (a few tens of KB). No ``data/`` dir is
read and nothing here runs during the test suite.

Known limitation: ``tiny_habitat.gpkg`` is not byte-reproducible because
GeoPackage records a creation timestamp in ``gpkg_contents``. Regenerating
it always shows a timestamp-only diff; the NetCDF and golden files are
byte-stable.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import xarray as xr
from shapely.geometry import Point

HERE = Path(__file__).resolve().parent
ABM = HERE.parents[1]  # mal-core/src/mal_core/abm
REPO = HERE.parents[5]
GOLDEN = ABM / "tests" / "golden"
ENGINE = ABM / "build" / "src" / "mal_abm_fast"

# 8x8 cells at 1000 m, near 5.7 N (same latitude as the old accra AOI).
# The 0.999 shrink keeps ceil() from rounding 8.0 up to 9.
METRES_PER_DEG_LAT = 111195.08023353292
N = 8
LAT0 = 5.70
DLAT = N * 1000.0 / METRES_PER_DEG_LAT
DLON = N * 1000.0 / (METRES_PER_DEG_LAT * math.cos(math.radians(LAT0)))
WEST, SOUTH = 0.0, LAT0
EAST = DLON * 0.999
NORTH = SOUTH + DLAT * 0.999

DAYS = 95


def _grid() -> tuple[np.ndarray, np.ndarray]:
    """Row (north->south) / col centres, matching the env producer order."""
    rows = np.array([NORTH - (r + 0.5) * (NORTH - SOUTH) / N for r in range(N)])
    cols = np.array([WEST + (c + 0.5) * (EAST - WEST) / N for c in range(N)])
    return rows, cols


def make_env(path: Path) -> None:
    time = np.arange(np.datetime64("2024-01-01"), np.datetime64("2024-01-01") + DAYS)
    # 25 mm every 5 days keeps the pluvial state alive between pulses.
    rain = np.zeros((DAYS, N, N), dtype=np.float32)
    rain[::5, :, :] = 25.0
    temp = np.full((DAYS, N, N), 26.0, dtype=np.float32)
    rr, cc = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    jrc = (0.30 + 0.02 * rr).astype(np.float32)
    built = np.full((N, N), 0.10, dtype=np.float32)
    wetland = np.full((N, N), 0.05, dtype=np.float32)
    openp = (0.05 + 0.01 * cc).astype(np.float32)
    crop = np.full((N, N), 0.05, dtype=np.float32)
    salinity = np.zeros((DAYS, N, N), dtype=np.float32)

    ds = xr.Dataset(
        {
            "rainfall": (("time", "y", "x"), rain),
            "air_temp_c": (("time", "y", "x"), temp),
            "jrc_persistent": (("y", "x"), jrc),
            "lc_built": (("y", "x"), built),
            "lc_wetland": (("y", "x"), wetland),
            "lc_open_plus_water": (("y", "x"), openp),
            "lc_crop": (("y", "x"), crop),
            "salinity_ppt": (("time", "y", "x"), salinity),
        },
        coords={"time": time, "y": np.arange(N), "x": np.arange(N)},
        attrs={
            "Conventions": "CF-1.8",
            "title": "MalariaSentinel tiny golden env tensor",
            "aoi_slug": "golden-tiny",
            "scale": "regional",
            "contract_version": "3.0",
        },
    )
    ds.to_netcdf(path)


def make_habitat(path: Path) -> None:
    rows, cols = _grid()
    rr, cc = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    potential = (0.55 + 0.03 * rr + 0.02 * cc).astype(float)
    records = []
    for r in range(N):
        for c in range(N):
            records.append(
                {
                    "hab_type": "open_pluvial",
                    "dynamics": 1,
                    "habitat_potential": float(potential[r, c]),
                    "row": r,
                    "col": c,
                    "aoi_slug": "golden-tiny",
                    "geometry": Point(float(cols[c]), float(rows[r])),
                }
            )
    gpd.GeoDataFrame(records, crs="EPSG:4326").to_file(path, driver="GPKG")


def make_hosts(path: Path) -> None:
    rows, cols = _grid()
    shape = (N, N)
    human = np.full(shape, 500.0, dtype=np.float32)
    human[0, 0] = 900.0
    cattle = np.full(shape, 200.0, dtype=np.float32)
    goats = np.full(shape, 100.0, dtype=np.float32)
    sheep = np.full(shape, 100.0, dtype=np.float32)
    pigs = np.full(shape, 20.0, dtype=np.float32)
    chickens = np.full(shape, 50.0, dtype=np.float32)
    wildlife = np.full(shape, 0.5, dtype=np.float32)
    urban = np.full(shape, 30, dtype=np.int32)
    urban[:, 4:] = 50

    ds = xr.Dataset(
        {
            "human": (("y", "x"), human),
            "cattle": (("y", "x"), cattle),
            "goats": (("y", "x"), goats),
            "sheep": (("y", "x"), sheep),
            "pigs": (("y", "x"), pigs),
            "chickens": (("y", "x"), chickens),
            "wildlife_host_proxy": (("y", "x"), wildlife),
            "urban_class": (("y", "x"), urban),
        },
        coords={
            "y": ("y", rows, {"axis": "Y"}),
            "x": ("x", cols, {"axis": "X"}),
        },
        attrs={
            "Conventions": "CF-1.8",
            "title": "MalariaSentinel tiny golden host density",
            "source_crs": "EPSG:4326",
        },
    )
    ds.to_netcdf(path)


def _run(out_dir: Path, days: int, extra: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(ENGINE), "run",
        "--bbox", f"{WEST},{SOUTH},{EAST},{NORTH}",
        "--crs", "EPSG:4326", "--resolution-m", "1000",
        "--year", "2024", "--month", "1", "--seed", "42",
        "--days", str(days),
        "--env", str(HERE / "tiny_env.nc"),
        "--habitat", str(HERE / "tiny_habitat.gpkg"),
        "--output", str(out_dir / "state.tif"),
        "--n-adults-per-detection", "1000",
        *extra,
    ]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=REPO)


def main() -> int:
    if not ENGINE.is_file():
        print(f"engine not built: {ENGINE}", file=sys.stderr)
        return 1
    make_env(HERE / "tiny_env.nc")
    make_habitat(HERE / "tiny_habitat.gpkg")
    make_hosts(HERE / "tiny_hosts.nc")

    GOLDEN.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="mal_abm_golden_gen_"))

    five = base / "five"
    _run(five, 5, [])
    shutil.copy2(five / "state.tif", GOLDEN / "state_seed42_day5.tif")
    shutil.copy2(five / "state.json", GOLDEN / "state_seed42_day5.json")
    shutil.copy2(five / "state_aquatic.json",
                 GOLDEN / "state_seed42_day5_aquatic.json")

    tx = base / "tx"
    _run(
        tx,
        90,
        [
            "--enable-transmission",
            "--hosts", str(HERE / "tiny_hosts.nc"),
            # Guarantee the vector→human branch of the chain on the tiny AOI.
            "--initial-vector-infected-frac", "0.2",
            "--emit-transmission-log", str(tx / "transmission_log.json"),
        ],
    )
    shutil.copy2(tx / "transmission_log.json",
                 GOLDEN / "transmission_seed42_day90.json")
    shutil.rmtree(base, ignore_errors=True)
    print("golden fixtures regenerated under", GOLDEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
