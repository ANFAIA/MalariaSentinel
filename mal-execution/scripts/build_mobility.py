#!/usr/bin/env python3
"""Build mobility OD matrices from host_static.nc.

Reads the static host density NetCDF and generates CSR files for the ABM
engine using a gravity model.

Outputs:
    - ``human_mobility_day.csr``    (low β → spread during daytime)
    - ``human_mobility_night.csr``  (high β → concentrated at night)
    - ``livestock_mobility_season.csr`` (medium β → seasonal movement)
    - ``mobility_manifest.json``

Usage::

    uv run python mal-execution/scripts/build_mobility.py \\
        --hosts hosts/host_static.nc \\
        --output-dir hosts/ \\
        --cell-size-km 1.0 \\
        --beta-day 0.05 \\
        --beta-night 0.5 \\
        --max-distance-km 50.0
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np

from mal_commonlib.data.mobility import (
    build_gravity_od,
    build_identity_od,
    write_csr,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build gravity-model mobility OD matrices from host_static.nc."
    )
    p.add_argument(
        "--hosts",
        type=pathlib.Path,
        required=True,
        help="Path to host_static.nc",
    )
    p.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=None,
        help="Output directory for CSR files (default: same directory as --hosts)",
    )
    p.add_argument(
        "--cell-size-km",
        type=float,
        default=1.0,
        help="Grid cell size in km (default: 1.0)",
    )
    p.add_argument(
        "--beta-day",
        type=float,
        default=0.05,
        help="Friction parameter for human daytime mobility (default: 0.05)",
    )
    p.add_argument(
        "--beta-night",
        type=float,
        default=0.5,
        help="Friction parameter for human nighttime mobility (default: 0.5)",
    )
    p.add_argument(
        "--beta-livestock",
        type=float,
        default=0.1,
        help="Friction parameter for livestock mobility (default: 0.1)",
    )
    p.add_argument(
        "--max-distance-km",
        type=float,
        default=50.0,
        help="Maximum mobility distance in km (default: 50.0)",
    )
    return p.parse_args()


def _load_host_data(hosts_path: pathlib.Path) -> dict[str, np.ndarray]:
    """Load variables from host_static.nc."""
    import xarray as xr

    ds = xr.open_dataset(str(hosts_path), engine="netcdf4")
    data = {}
    for var in ds.data_vars:
        if var in ("crs",):
            continue
        data[var] = ds[var].values.astype(np.float32)
    ds.close()
    return data


def main() -> None:
    args = _parse_args()

    if not args.hosts.exists():
        print(f"Error: {args.hosts} not found", file=sys.stderr)
        sys.exit(1)

    out_dir = args.output_dir or args.hosts.parent

    print(f"Loading: {args.hosts}")
    host_data = _load_host_data(args.hosts)
    print(f"  Variables: {list(host_data.keys())}")
    shape = next(iter(host_data.values())).shape
    H, W = shape
    n_cells = H * W
    print(f"  Grid: {H} × {W} = {n_cells:,} cells")

    # --- Human attractiveness = human population ---
    human = host_data.get("human", np.zeros(shape, dtype=np.float32))
    human_total = float(human[human != -9999.0].sum()) if (human == -9999.0).any() else float(human.sum())
    print(f"  Human total: {human_total:,.0f}")

    # --- Livestock attractiveness = sum of livestock species ---
    livestock_vars = ["cattle", "goats", "sheep", "pigs", "chickens"]
    livestock = np.zeros(shape, dtype=np.float32)
    for var in livestock_vars:
        if var in host_data:
            arr = host_data[var]
            livestock += np.where(arr == -9999.0, 0.0, arr)
    livestock_total = float(livestock.sum())
    print(f"  Livestock total: {livestock_total:,.0f}")

    # --- Build OD matrices ---
    t0 = time.time()

    print(f"\nBuilding human daytime OD (β={args.beta_day}, max={args.max_distance_km}km)...")
    rp_hday, ci_hday, v_hday, nr, nc = build_gravity_od(
        human, args.cell_size_km, args.beta_day, args.max_distance_km
    )
    print(f"  nnz: {len(ci_hday):,} ({len(ci_hday)/n_cells:.1f} entries/cell)")

    print(f"\nBuilding human nighttime OD (β={args.beta_night}, max={args.max_distance_km}km)...")
    rp_hnight, ci_hnight, v_hnight, _, _ = build_gravity_od(
        human, args.cell_size_km, args.beta_night, args.max_distance_km
    )
    print(f"  nnz: {len(ci_hnight):,} ({len(ci_hnight)/n_cells:.1f} entries/cell)")

    if livestock_total > 0:
        print(f"\nBuilding livestock seasonal OD (β={args.beta_livestock}, max={args.max_distance_km}km)...")
        rp_live, ci_live, v_live, _, _ = build_gravity_od(
            livestock, args.cell_size_km, args.beta_livestock, args.max_distance_km
        )
        print(f"  nnz: {len(ci_live):,} ({len(ci_live)/n_cells:.1f} entries/cell)")
    else:
        print("\nNo livestock data — using identity OD")
        rp_live, ci_live, v_live, nr, nc = build_identity_od(n_cells)

    elapsed = time.time() - t0

    # --- Write CSR files ---
    out_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "human_mobility_day.csr": (rp_hday, ci_hday, v_hday),
        "human_mobility_night.csr": (rp_hnight, ci_hnight, v_hnight),
        "livestock_mobility_season.csr": (rp_live, ci_live, v_live),
    }
    for name, (rp, ci, vl) in files.items():
        p = write_csr(rp, ci, vl, nr, nc, out_dir / name)
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f"  Written: {p} ({size_mb:.1f} MB)")

    # --- Manifest ---
    manifest = {
        "n_cells": n_cells,
        "grid_height": H,
        "grid_width": W,
        "cell_size_km": args.cell_size_km,
        "beta_day": args.beta_day,
        "beta_night": args.beta_night,
        "beta_livestock": args.beta_livestock,
        "max_distance_km": args.max_distance_km,
        "human_total": human_total,
        "livestock_total": livestock_total,
        "build_time_s": round(elapsed, 2),
    }
    manifest_path = out_dir / "mobility_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nManifest: {manifest_path}")
    print(f"Done in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
