#!/usr/bin/env python3
"""Build the synthetic 10x10 AOI used by the scenario harness (plan §13.1).

Resamples the Accra test window (``data/accra-coastal-test/``) onto a 10x10
grid covering the ``accra-synth-10x10`` bounding box and writes, under
``<out>`` (default ``runs/synthetic/accra-synth-10x10``):

* ``*_regional_2024_2024_env.nc``  env NetCDF, contract ``env_nc`` 3.0 with
  the nine variables the C++ reader needs (rainfall, air_temp_c, five habitat
  statics, land_frac, salinity_ppt);
* ``*_habitat_patches.gpkg``      one Point per candidate cell (dynamics as
  int 0 persistent / 1 pluvial, potential recomputed with
  ``mal_core.habitat.potential``, cells below the engine floor dropped and
  counted);
* ``*_host_static.nc``            nine (y, x) host planes;
* ``*_wind_6hourly_2024_2024_daily.nc``  u100/v100 on the same cells, for
  ``--wind-field``;
* ``scenarios/*.json``            copies of the scenario definitions;
* ``manifest.json``               written through ``mal_core.download.manifest``.

Regridding is conservative: intensive quantities (rain, temperature,
fractions, potential inputs) are overlap-area means, extensive counts
(population, livestock) are overlap-area sums, and categorical urban class
takes the source cell with the largest overlap. Nothing is random: two runs
produce byte-identical NetCDF files (the GeoPackage is exempt: it stamps
``gpkg_contents.last_change``).

Usage (from the repository root)::

    uv run python mal-execution/scripts/make_synthetic_aoi.py \\
        --out runs/synthetic/accra-synth-10x10 \\
        [--scenario E00]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import xarray as xr
from shapely.geometry import Point

from mal_commonlib.aoi import AOI
from mal_core.download.manifest import update_dataset, validate_completeness
from mal_core.habitat import potential as _pot
from mal_core.habitat.config import CONFIG, dynamics_map, habitat_names

REPO = Path(__file__).resolve().parents[2]

SLUG = "accra-synth-10x10"
BBOX = (-0.2, 5.7, -0.10971147034573944, 5.789842104336081)  # W, S, E, N
CRS = "EPSG:4326"
RES_M = 1000
N = 10
YEAR = 2024

ENV_VARS = (
    "rainfall", "air_temp_c",
    "jrc_persistent", "lc_built", "lc_wetland", "lc_open_plus_water", "lc_crop",
    "land_frac", "salinity_ppt",
)
HOST_VARS = (
    "human", "cattle", "goats", "sheep", "pigs", "chickens",
    "urban_class", "building_fraction", "wildlife_host_proxy",
)
EXTENSIVE_HOST = {"human", "cattle", "goats", "sheep", "pigs", "chickens"}
STATIC_FEATURES = ("jrc_persistent", "lc_wetland", "lc_built",
                   "lc_open_plus_water", "lc_crop")


# -- grid geometry ------------------------------------------------------------

def _centre_edges(c: np.ndarray) -> np.ndarray:
    """Cell edges (len n+1) for uniformly spaced cell centres, same direction."""
    step = (c[-1] - c[0]) / (len(c) - 1)
    return np.concatenate([[c[0] - step / 2], c + step / 2])


def _overlap(src_edges: np.ndarray, tgt_edges: np.ndarray) -> np.ndarray:
    """(n_tgt, n_src) overlap length of every target cell with every source cell."""
    s_lo, s_hi = np.minimum(src_edges[:-1], src_edges[1:]), np.maximum(src_edges[:-1], src_edges[1:])
    t_lo, t_hi = np.minimum(tgt_edges[:-1], tgt_edges[1:]), np.maximum(tgt_edges[:-1], tgt_edges[1:])
    ov = np.minimum(t_hi[:, None], s_hi[None, :]) - np.maximum(t_lo[:, None], s_lo[None, :])
    return np.clip(ov, 0.0, None)


class Regridder:
    """Separable conservative regridder between two regular lat/lon grids."""

    def __init__(self, src_lat: np.ndarray, src_lon: np.ndarray,
                 tgt_lat_edges: np.ndarray, tgt_lon_edges: np.ndarray):
        src_lat_e = _centre_edges(np.asarray(src_lat, float))
        src_lon_e = _centre_edges(np.asarray(src_lon, float))
        self.wy = _overlap(src_lat_e, tgt_lat_edges)            # (N, ny) lengths
        self.wx = _overlap(src_lon_e, tgt_lon_edges)            # (N, nx) lengths
        self.fy = self.wy / np.abs(np.diff(src_lat_e))[None, :]  # fraction of source cell
        self.fx = self.wx / np.abs(np.diff(src_lon_e))[None, :]
        # Target cell with no overlap would divide by zero below.
        assert (self.wy.sum(axis=1) > 0).all() and (self.wx.sum(axis=1) > 0).all()

    def mean(self, v: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        """Overlap-area mean over the last two axes; 0 where no valid source cell."""
        v = np.asarray(v, np.float64)
        m = np.ones_like(v) if mask is None else np.asarray(mask, np.float64)
        num = np.einsum("ia,...ab,jb->...ij", self.wy, v * m, self.wx)
        den = np.einsum("ia,...ab,jb->...ij", self.wy, m, self.wx)
        return np.where(den > 0, num / np.where(den > 0, den, 1.0), 0.0)

    def total(self, v: np.ndarray) -> np.ndarray:
        """Area-conserving sum: each source cell contributes its overlapping share."""
        v = np.asarray(v, np.float64)
        return np.einsum("ia,...ab,jb->...ij", self.fy, v, self.fx)

    def dominant(self, v: np.ndarray) -> np.ndarray:
        """Value of the source cell with the largest overlap for each target cell."""
        a = np.argmax(self.wy, axis=1)
        b = np.argmax(self.wx, axis=1)
        return np.asarray(v)[np.ix_(a, b)]


# -- helpers ------------------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _src_file(src: Path, suffix: str) -> Path:
    p = src / f"{src.name}_{suffix}"
    if not p.exists():
        raise FileNotFoundError(f"missing source file: {p}")
    return p


def _nc_encoding(ds: xr.Dataset) -> dict:
    level = int(CONFIG["ingest"]["nc_compression_level"])
    return {v: {"dtype": "float32", "zlib": True, "complevel": level}
            for v in ds.data_vars if ds[v].dtype.kind == "f"}


def _fresh_path(path: Path) -> Path:
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# -- builders -----------------------------------------------------------------

def build_env(src: Path, out: Path, grid: dict, rg: Regridder) -> tuple[Path, np.ndarray]:
    """Write env.nc; return its path and the resampled static features."""
    with xr.open_dataset(_src_file(src, "regional_2024_2024_env.nc")) as env:
        env = env.load()
    contract = str(CONFIG["contracts"]["env_nc"])
    if str(env.attrs.get("contract_version")) != contract:
        raise ValueError(f"source env contract {env.attrs.get('contract_version')!r} != {contract!r}")
    missing = [v for v in ENV_VARS if v not in env]
    if missing:
        raise ValueError(f"source env is missing {missing}")

    data = {}
    for v in ENV_VARS:
        arr = np.nan_to_num(env[v].values.astype(np.float64), nan=0.0)
        if v == "air_temp_c":
            # 0.0 is the open-sea sentinel: average only over non-sea source cells.
            data[v] = rg.mean(arr, mask=(arr != 0.0)).astype(np.float32)
        else:
            data[v] = rg.mean(arr).astype(np.float32)
    # Clip intensive fractions into [0, 1] (regridding a [0,1] field stays in range; guard anyway).
    for v in ("jrc_persistent", "lc_built", "lc_wetland", "lc_open_plus_water", "lc_crop", "land_frac"):
        data[v] = np.clip(data[v], 0.0, 1.0).astype(np.float32)

    statics = {k: data[k].astype(np.float64) for k in STATIC_FEATURES}
    h_total = np.asarray(_pot.total_potential(_pot.static_potential(statics)), dtype=np.float64)
    n_candidates = int((h_total > float(CONFIG["ingest"]["candidate_min_ingest"])).sum())

    attrs = dict(env.attrs)  # the source's n_candidate_cells is NOT this AOI's: replaced below
    attrs.update({
        "title": f"MalariaSentinel synthetic daily env tensor — {SLUG}",
        "aoi_slug": SLUG,
        "generator_version": "make_synthetic_aoi-0.1",
        "contract_version": contract,
        "n_candidate_cells": n_candidates,
    })
    ds = xr.Dataset(
        {
            "rainfall": (("time", "y", "x"), data["rainfall"], dict(env.rainfall.attrs)),
            "air_temp_c": (("time", "y", "x"), data["air_temp_c"], dict(env.air_temp_c.attrs)),
            "jrc_persistent": (("y", "x"), data["jrc_persistent"], dict(env.jrc_persistent.attrs)),
            "lc_built": (("y", "x"), data["lc_built"], dict(env.lc_built.attrs)),
            "lc_wetland": (("y", "x"), data["lc_wetland"], dict(env.lc_wetland.attrs)),
            "lc_open_plus_water": (("y", "x"), data["lc_open_plus_water"], dict(env.lc_open_plus_water.attrs)),
            "lc_crop": (("y", "x"), data["lc_crop"], dict(env.lc_crop.attrs)),
            "land_frac": (("y", "x"), data["land_frac"], dict(env.land_frac.attrs)),
            "salinity_ppt": (("time", "y", "x"), data["salinity_ppt"], dict(env.salinity_ppt.attrs)),
        },
        coords={"time": env.time.values, "y": np.arange(N), "x": np.arange(N)},
        attrs=attrs,
    )
    path = _fresh_path(out / f"{SLUG}_regional_{YEAR}_{YEAR}_env.nc")
    ds.to_netcdf(path, encoding=_nc_encoding(ds))
    return path, statics


def build_habitat(out: Path, grid: dict, statics: dict[str, np.ndarray]) -> tuple[Path, dict]:
    """Write the candidate-patch GeoPackage; return its path and the census."""
    h_static = _pot.static_potential(statics)
    h_total = np.asarray(_pot.total_potential(h_static), dtype=np.float64)

    ingest_floor = float(CONFIG["ingest"]["candidate_min_ingest"])
    engine_floor = float(CONFIG["habitat"]["candidate_min_engine"])
    above_ingest = h_total > ingest_floor
    keep = above_ingest & (h_total >= engine_floor)
    census = {
        "cells_total": int(h_total.size),
        "cells_above_ingest_floor": int(above_ingest.sum()),
        "dropped_below_engine_floor": int((above_ingest & ~keep).sum()),
        "patches_written": int(keep.sum()),
        "engine_floor": engine_floor,
    }
    print(f"candidate census: {census}")

    dyn = dynamics_map()
    dyn_int = {"persistent": 0, "pluvial": 1}
    types = list(habitat_names())
    rows, cols = np.nonzero(keep)
    lat_c, lon_c = grid["lat_c"], grid["lon_c"]
    dominant = [max(types, key=lambda g: float(h_static[g][r, c])) for r, c in zip(rows, cols)]

    data = {
        "hab_type": np.array(dominant, dtype=object),
        "dynamics": np.array([dyn_int[dyn[g]] for g in dominant], dtype=np.int32),
        "habitat_potential": h_total[rows, cols],
        "row": rows.astype(np.int32),
        "col": cols.astype(np.int32),
        "aoi_slug": np.array([SLUG] * len(rows), dtype=object),
    }
    for g in types:
        data[f"hab_{g}"] = np.asarray(h_static[g], dtype=np.float64)[rows, cols]

    gdf = gpd.GeoDataFrame(
        data,
        geometry=[Point(float(lon_c[c]), float(lat_c[r])) for r, c in zip(rows, cols)],
        crs=CRS,
    )
    path = _fresh_path(out / f"{SLUG}_habitat_patches.gpkg")
    gdf.to_file(path, driver="GPKG")
    return path, census


def build_hosts(src: Path, out: Path, rg: Regridder, grid: dict) -> Path:
    with xr.open_dataset(_src_file(src, "host_static.nc")) as hs:
        hs = hs.load()
    missing = [v for v in HOST_VARS if v not in hs]
    if missing:
        raise ValueError(f"source host_static is missing {missing}")
    ds_vars = {}
    for v in HOST_VARS:
        arr = hs[v].values
        if v == "urban_class":
            ds_vars[v] = (("y", "x"), rg.dominant(arr).astype(np.int32))
        elif v in EXTENSIVE_HOST:
            ds_vars[v] = (("y", "x"), rg.total(np.nan_to_num(arr, nan=0.0)).astype(np.float32))
        else:
            ds_vars[v] = (("y", "x"), rg.mean(np.nan_to_num(arr, nan=0.0)).astype(np.float32))
    ds = xr.Dataset(
        ds_vars,
        coords={
            "y": ("y", grid["lat_c"], {"axis": "Y"}),
            "x": ("x", grid["lon_c"], {"axis": "X"}),
        },
        attrs={
            "Conventions": "CF-1.8",
            "title": f"MalariaSentinel synthetic static host density — {SLUG}",
            "source_crs": CRS,
            "grid_height": N,
            "grid_width": N,
            "generator_version": "make_synthetic_aoi-0.1",
        },
    )
    path = _fresh_path(out / f"{SLUG}_host_static.nc")
    ds.to_netcdf(path, encoding=_nc_encoding(ds))
    return path


def build_wind(src: Path, out: Path, grid: dict) -> Path:
    with xr.open_dataset(_src_file(src, "wind_6hourly_2024_2024_daily.nc")) as w:
        w = w[["u100", "v100"]].load()
    w = w.drop_vars([c for c in ("expver", "number") if c in w.coords], errors="ignore")
    interp = w.interp(latitude=grid["lat_c"], longitude=grid["lon_c"], method="linear")
    interp = interp.transpose("valid_time", "latitude", "longitude")
    interp.attrs = {"title": f"ERA5 100 m wind, resampled to {SLUG}"}
    n_times = interp.sizes["valid_time"]
    if n_times % 4 != 0:
        raise ValueError(f"wind has {n_times} time steps; the reader needs a multiple of 4")
    path = _fresh_path(out / f"{SLUG}_wind_6hourly_{YEAR}_{YEAR}_daily.nc")
    interp.to_netcdf(path, encoding=_nc_encoding(interp))
    return path


def copy_scenarios(scen_dir: Path, out: Path) -> list[str]:
    dest = out / "scenarios"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ids = []
    for src_json in sorted(scen_dir.glob("*.json")):
        json.loads(src_json.read_text())  # fail early on malformed JSON
        shutil.copy2(src_json, dest / src_json.name)
        ids.append(src_json.stem)
    return ids


def write_manifest(out: Path, files: dict, scenario_id: str | None) -> None:
    manifest = out / "manifest.json"
    if manifest.exists():
        manifest.unlink()  # stale scenario keys must not survive a rebuild
    root = out.parent
    update_dataset(SLUG, "env", YEAR, files["env"], type="time-series", format="nc",
                   required_for_abm=True, period={"start": f"{YEAR}-01-01", "end": f"{YEAR}-12-31"},
                   data_root=root)
    update_dataset(SLUG, "habitat", None, files["habitat"], type="static", format="gpkg",
                   required_for_abm=True, data_root=root)
    update_dataset(SLUG, "host_static", None, files["host_static"], type="static", format="nc",
                   required_for_abm=True, data_root=root)
    update_dataset(SLUG, "wind", None, files["wind"], type="time-series", format="nc",
                   required_for_abm=False, period={"start": f"{YEAR}-06-01", "end": f"{YEAR}-06-30"},
                   data_root=root)
    if scenario_id is not None:
        # files == {"<id>": "scenarios/<id>.json"}: year=<id> keys the file by its id.
        update_dataset(SLUG, f"scenario:{scenario_id}", scenario_id,
                       f"scenarios/{scenario_id}.json", type="static", format="json",
                       required_for_abm=False, data_root=root)


# -- main ---------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=REPO / "runs" / "synthetic" / SLUG,
                    help="AOI directory to write (its name must be the slug %(default)s)")
    ap.add_argument("--src", type=Path, default=REPO / "data" / "accra-coastal-test",
                    help="source Accra test window (read only)")
    ap.add_argument("--scenarios-dir", type=Path,
                    default=REPO / "mal-core" / "src" / "mal_core" / "abm" / "tests" / "scenarios")
    ap.add_argument("--scenario", default=None,
                    help="scenario id to declare in the manifest (e.g. E00)")
    args = ap.parse_args(argv)

    out = args.out.resolve()
    if out.name != SLUG:
        ap.error(f"--out directory must be named {SLUG!r}, got {out.name!r}")

    aoi = AOI.from_bbox(*BBOX, crs=CRS, slug=SLUG, resolution_m=RES_M)
    if aoi.cells_per_side() != (N, N):
        raise RuntimeError(f"bbox gives {aoi.cells_per_side()} cells, expected {(N, N)}")
    print(f"AOI {SLUG}: cells {aoi.cells_per_side()}, width {aoi.width_m:.1f} m, height {aoi.height_m:.1f} m")

    w, s, e, n = BBOX
    lat_edges = np.linspace(n, s, N + 1)
    lon_edges = np.linspace(w, e, N + 1)
    grid = {
        "lat_c": (lat_edges[:-1] + lat_edges[1:]) / 2,
        "lon_c": (lon_edges[:-1] + lon_edges[1:]) / 2,
    }
    with xr.open_dataset(_src_file(args.src, "host_static.nc")) as hs:
        src_lat, src_lon = hs.y.values, hs.x.values
    # env and host share the 56x61 source grid (verified: same shape, row 0 = north).
    rg = Regridder(src_lat, src_lon, lat_edges, lon_edges)

    out.mkdir(parents=True, exist_ok=True)
    env_path, statics = build_env(args.src, out, grid, rg)
    hab_path, census = build_habitat(out, grid, statics)
    host_path = build_hosts(args.src, out, rg, grid)
    wind_path = build_wind(args.src, out, grid)

    scen_ids = copy_scenarios(args.scenarios_dir, out)
    if args.scenario is not None and args.scenario not in scen_ids:
        raise FileNotFoundError(f"scenario {args.scenario!r} not found in {args.scenarios_dir}")
    print(f"scenarios copied: {len(scen_ids)} -> {out / 'scenarios'}")

    files = {"env": env_path.name, "habitat": hab_path.name,
             "host_static": host_path.name, "wind": wind_path.name}
    write_manifest(out, files, args.scenario)

    for p in (env_path, host_path, wind_path, hab_path, out / "manifest.json"):
        print(f"wrote {p}")
    print(f"sha256 env.nc       {_sha256(env_path)}")
    print(f"sha256 host_static  {_sha256(host_path)}")
    print(f"sha256 wind.nc      {_sha256(wind_path)}")
    print(f"census {census}")
    missing = validate_completeness(SLUG, data_root=out.parent)
    print(f"validate_completeness: {missing or 'OK (no missing files)'}")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
