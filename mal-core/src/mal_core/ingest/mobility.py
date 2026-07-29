"""Ingest stage — build mobility OD matrices from host_static.nc.

Extracted from mal-execution/scripts/build_mobility.py.
Core logic preserved; CLI layer removed.
"""
from __future__ import annotations

import json
import pathlib
import time

import numpy as np
import xarray as xr

from mal_commonlib.data.mobility import (
    build_gravity_od,
    build_identity_od,
    write_csr,
)

from ._shared import register_dataset


def _load_host_data(hosts_path: pathlib.Path) -> dict[str, np.ndarray]:
    """Load variables from host_static.nc."""
    ds = xr.open_dataset(str(hosts_path), engine="netcdf4")
    data = {}
    for var in ds.data_vars:
        if var in ("crs",):
            continue
        data[var] = ds[var].values.astype(np.float32)
    ds.close()
    return data


def build_mobility_dataset(
    hosts_path: pathlib.Path,
    *,
    output_dir: pathlib.Path,
    aoi_slug: str = "ghana",
    cell_size_km: float = 1.0,
    beta_day: float = 0.05,
    beta_night: float = 0.5,
    beta_livestock: float = 0.1,
    max_distance_km: float = 50.0,
) -> dict:
    """Build gravity-model mobility OD matrices from host_static.nc.

    Args:
        hosts_path: path to host_static.nc.
        output_dir: directory for CSR files.
        aoi_slug: AOI identifier for manifest registration.
        cell_size_km: grid cell size in km.
        beta_day: friction for human daytime mobility.
        beta_night: friction for human nighttime mobility.
        beta_livestock: friction for livestock mobility.
        max_distance_km: maximum mobility distance.

    Returns:
        dict with 'files', 'manifest_path', and stats.
    """
    if not hosts_path.exists():
        raise FileNotFoundError(f"host_static.nc not found: {hosts_path}")

    host_data = _load_host_data(hosts_path)
    shape = next(iter(host_data.values())).shape
    H, W = shape
    n_cells = H * W

    # Human attractiveness = human population
    human = host_data.get("human", np.zeros(shape, dtype=np.float32))
    human_total = float(human[human != -9999.0].sum()) if (human == -9999.0).any() else float(human.sum())

    # Livestock attractiveness = sum of livestock species
    livestock_vars = ["cattle", "goats", "sheep", "pigs", "chickens"]
    livestock = np.zeros(shape, dtype=np.float32)
    for var in livestock_vars:
        if var in host_data:
            arr = host_data[var]
            livestock += np.where(arr == -9999.0, 0.0, arr)
    livestock_total = float(livestock.sum())

    # Build OD matrices
    t0 = time.time()

    rp_hday, ci_hday, v_hday, nr, nc = build_gravity_od(
        human, cell_size_km, beta_day, max_distance_km,
    )

    rp_hnight, ci_hnight, v_hnight, _, _ = build_gravity_od(
        human, cell_size_km, beta_night, max_distance_km,
    )

    if livestock_total > 0:
        rp_live, ci_live, v_live, _, _ = build_gravity_od(
            livestock, cell_size_km, beta_livestock, max_distance_km,
        )
    else:
        rp_live, ci_live, v_live, nr, nc = build_identity_od(n_cells)

    elapsed = time.time() - t0

    # Write CSR files
    output_dir.mkdir(parents=True, exist_ok=True)

    csr_files = {
        f"{aoi_slug}_mobility_day.csr": (rp_hday, ci_hday, v_hday),
        f"{aoi_slug}_mobility_night.csr": (rp_hnight, ci_hnight, v_hnight),
        f"{aoi_slug}_livestock_mobility.csr": (rp_live, ci_live, v_live),
    }
    written_paths: list[str] = []
    for name, (rp, ci, vl) in csr_files.items():
        p = write_csr(rp, ci, vl, nr, nc, output_dir / name)
        written_paths.append(str(p))

    # Write manifest
    manifest = {
        "n_cells": n_cells,
        "grid_height": H,
        "grid_width": W,
        "cell_size_km": cell_size_km,
        "beta_day": beta_day,
        "beta_night": beta_night,
        "beta_livestock": beta_livestock,
        "max_distance_km": max_distance_km,
        "human_total": human_total,
        "livestock_total": livestock_total,
        "build_time_s": round(elapsed, 2),
    }
    manifest_path = output_dir / "mobility_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    # Register in central manifest
    manifest_keys = {
        f"{aoi_slug}_mobility_day.csr": "mobility_day",
        f"{aoi_slug}_mobility_night.csr": "mobility_night",
        f"{aoi_slug}_livestock_mobility.csr": "livestock_mobility",
    }
    for csr_name, manifest_key in manifest_keys.items():
        register_dataset(
            aoi_slug, manifest_key, None,
            csr_name,
            required_for_abm=True,
        )
    register_dataset(
        aoi_slug, "mobility_manifest", None,
        str(manifest_path.name),
    )

    return {
        "files": written_paths,
        "manifest_path": str(manifest_path),
        "n_cells": n_cells,
        "human_total": human_total,
        "livestock_total": livestock_total,
        "build_time_s": round(elapsed, 2),
    }
