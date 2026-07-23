#!/usr/bin/env python3
"""M7 — Build static host density NetCDF for the ABM engine.

Downloads WorldPop Ghana population, FAO GLW4 livestock, and GHSL
settlement classification, aggregates them to the ABM grid, and writes
``hosts/host_static.nc`` + ``hosts/host_manifest.json``.

Usage:
    uv run python mal-execution/scripts/build_hosts.py [--output-dir DIR] [--aoi AOI_JSON]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

from mal_commonlib.aoi import AOI
from mal_commonlib.config import AOI_E, AOI_N, AOI_S, AOI_W, DST_CRS, DST_RES
from mal_commonlib.data.host_utils import (
    aggregate_to_grid,
    build_host_static_nc,
    write_manifest,
)
from mal_commonlib.data.loaders.ghsl import GHSLLoader, GHSL_RURAL, GHSL_URBAN
from mal_commonlib.data.loaders.glw import GLWLoader
from mal_commonlib.data.loaders.worldpop import WorldPopLoader


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build static host density NetCDF for the ABM engine."
    )
    p.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=pathlib.Path("hosts"),
        help="Output directory for host_static.nc and host_manifest.json (default: hosts/)",
    )
    p.add_argument(
        "--aoi",
        type=str,
        default=None,
        help="Path to AOI JSON file. If not provided, uses the default Ghana AOI from config.",
    )
    p.add_argument(
        "--bbox",
        type=str,
        default=None,
        help='Custom bbox "W,S,E,N" in degrees (overrides --aoi and config).',
    )
    p.add_argument(
        "--worldpop-year",
        type=int,
        default=2019,
        help="WorldPop year (default: 2019, only Ghana constrained available)",
    )
    p.add_argument(
        "--cache-dir",
        type=pathlib.Path,
        default=None,
        help="Cache directory for downloads (default: XDG_CACHE_HOME/mal_commonlib/)",
    )
    return p.parse_args()


def _get_aoi(aoi_path: str | None, bbox_str: str | None) -> AOI:
    """Load or construct the AOI."""
    if bbox_str is not None:
        parts = [p.strip() for p in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError(f"--bbox must be 4 floats 'W,S,E,N'; got {bbox_str!r}")
        w, s, e, n = (float(x) for x in parts)
        return AOI.from_bbox(w, s, e, n, crs="EPSG:4326", slug="custom", resolution_m=DST_RES)
    if aoi_path is not None:
        return AOI.from_file(aoi_path)
    # Use WGS84 for the bbox (the default registry values are in degrees).
    return AOI.from_bbox(
        AOI_W, AOI_S, AOI_E, AOI_N,
        crs="EPSG:4326",
        slug="ghana",
        resolution_m=DST_RES,
    )


def main() -> None:
    args = _parse_args()

    aoi = _get_aoi(args.aoi, args.bbox)
    print(f"AOI: {aoi.slug} ({aoi.bbox})")
    print(f"CRS: {aoi.crs}, resolution: {aoi.resolution_m} m")
    h, w = aoi.cells_per_side()
    print(f"Grid: {h} x {w} cells")

    # Target grid spec for the ABM
    from rasterio.transform import from_bounds
    target_transform = from_bounds(*aoi.bbox, w, h)
    grid_spec = {
        "crs": aoi.crs,
        "transform": target_transform,
        "height": h,
        "width": w,
    }

    cache = args.cache_dir

    # 1. Human population (WorldPop, ~100m) — sum-preserving aggregation
    print("\n[1/4] Loading WorldPop human population...")
    wp = WorldPopLoader()
    pop_da = wp.load(aoi, year=args.worldpop_year, cache_dir=cache)
    human = aggregate_to_grid(
        pop_da.values,
        pop_da.rio.transform(),
        pop_da.rio.crs,
        target_transform,
        aoi.crs_obj,
        (h, w),
        method="sum",
    )
    print(f"  Human total: {human[human != -9999.0].sum():,.0f} persons")

    # 2. Livestock (GLW4, ~10km) — sum-preserving aggregation
    glw = GLWLoader()
    livestock_totals = {}

    print("\n[2/4] Loading GLW4 livestock...")
    for species in ["cattle", "goats", "sheep"]:
        print(f"  Loading {species}...")
        livestock_da = glw.load(aoi, species=species, cache_dir=cache)
        livestock_arr = aggregate_to_grid(
            livestock_da.values,
            livestock_da.rio.transform(),
            livestock_da.rio.crs,
            target_transform,
            aoi.crs_obj,
            (h, w),
            method="sum",
        )
        livestock_totals[species] = livestock_arr
        total = livestock_arr[livestock_arr != -9999.0].sum()
        print(f"  {species}: {total:,.0f} animals")

    # 3. Urban/rural classification (GHSL, 250m) — nearest-neighbour
    print("\n[3/4] Loading GHSL settlement classification...")
    try:
        ghsl = GHSLLoader()
        smod_da = ghsl.load(aoi, cache_dir=cache)
        urban_class = aggregate_to_grid(
            smod_da.values.astype(np.float32),
            smod_da.rio.transform(),
            smod_da.rio.crs,
            target_transform,
            aoi.crs_obj,
            (h, w),
            method="nearest",
        )
        urban_class = urban_class.astype(np.int32)
        n_urban = int((urban_class == GHSL_URBAN).sum())
        n_rural = int((urban_class == GHSL_RURAL).sum())
        print(f"  Urban cells: {n_urban}, Rural cells: {n_rural}")
    except Exception as exc:
        print(f"  WARNING: GHSL load failed: {exc}", file=sys.stderr)
        print("  Filling urban_class with rural default (50).", file=sys.stderr)
        urban_class = np.full((h, w), GHSL_RURAL, dtype=np.int32)

    # 4. Write NetCDF + manifest
    print("\n[4/4] Writing host_static.nc + manifest...")
    out_path = args.output_dir / "host_static.nc"
    build_host_static_nc(
        human=human,
        cattle=livestock_totals["cattle"],
        goats=livestock_totals["goats"],
        sheep=livestock_totals["sheep"],
        urban_class=urban_class,
        output_path=out_path,
        grid_spec=grid_spec,
    )
    manifest_path = write_manifest(
        output_path=out_path,
        human=human,
        cattle=livestock_totals["cattle"],
        goats=livestock_totals["goats"],
        sheep=livestock_totals["sheep"],
        urban_class=urban_class,
        grid_spec=grid_spec,
    )
    print(f"  Written: {out_path}")
    print(f"  Manifest: {manifest_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
