"""Ingest stage — build static host density NetCDF for the ABM engine.

Extracted from mal-execution/scripts/build_hosts.py.
Core logic preserved; CLI layer removed.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
from rasterio.transform import from_bounds

from mal_commonlib.aoi import AOI
from mal_commonlib.config import AOI_E, AOI_N, AOI_S, AOI_W, DST_CRS, DST_RES
from mal_commonlib.data.host_utils import (
    aggregate_to_grid,
    build_host_static_nc,
    write_manifest,
)
from mal_commonlib.data.loaders.ghsl import load_ghsl_urban_class
from mal_commonlib.data.loaders.glw import load_glw_livestock
from mal_commonlib.data.loaders.worldpop import load_worldpop_population

from ._shared import register_dataset

LIVESTOCK_SPECIES: list[str] = ["cattle", "goats", "sheep", "pigs", "chickens"]


def build_host_dataset(
    aoi: AOI,
    *,
    output_dir: pathlib.Path,
    worldpop_year: int = 2019,
    cache_dir: pathlib.Path | None = None,
    skip_buildings: bool = False,
    skip_wildlife: bool = False,
) -> dict:
    """Build static host density NetCDF for the ABM engine.

    Args:
        aoi: the AOI object.
        output_dir: directory for host_static.nc + manifest.
        worldpop_year: WorldPop product year.
        cache_dir: local cache for downloads.
        skip_buildings: skip Overture buildings (use urban_class heuristic).
        skip_wildlife: skip wildlife host proxy (use constant 0.3).

    Returns:
        dict with 'nc_path', 'manifest_path', and stats.
    """
    h, w = aoi.cells_per_side()
    target_transform = from_bounds(*aoi.bbox, w, h)
    grid_spec = {
        "crs": aoi.crs,
        "transform": target_transform,
        "height": h,
        "width": w,
    }

    results: dict = {
        "aoi_slug": aoi.slug,
        "grid": f"{h}x{w}",
    }

    # 1. Human population (WorldPop, ~100m) — sum-preserving aggregation
    pop_da = load_worldpop_population(aoi, year=worldpop_year, cache_dir=cache_dir)
    human = aggregate_to_grid(
        pop_da.values,
        pop_da.rio.transform(),
        pop_da.rio.crs,
        target_transform,
        aoi.crs_obj,
        (h, w),
        method="sum",
    )
    human_total = float(human[human != -9999.0].sum()) if (human == -9999.0).any() else float(human.sum())
    results["human_total"] = human_total

    # 2. Livestock (GLW4, ~10km) — sum-preserving aggregation
    livestock_totals: dict[str, np.ndarray] = {}

    for species in LIVESTOCK_SPECIES:
        livestock_da = load_glw_livestock(aoi, species=species, cache_dir=cache_dir)
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

    livestock_total = sum(
        float(arr[arr != -9999.0].sum()) for arr in livestock_totals.values()
    )
    results["livestock_total"] = livestock_total

    # 3. Urban/rural classification (GHSL, 250m) — nearest-neighbour
    try:
        smod_da = load_ghsl_urban_class(aoi, cache_dir=cache_dir)
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
        # Reclassify GHSL SMOD R2023A classes:
        #   30 → 30 (urban), 20-29 → 50 (rural), 0-19 → 20 (water)
        reclassified = np.where(urban_class == 30, 30, np.where(
            (urban_class >= 20) & (urban_class < 30), 50,
            np.where((urban_class >= 0) & (urban_class < 20), 20, 50)
        )).astype(np.int32)
        urban_class = reclassified
        n_urban = int((urban_class == 30).sum())
        n_rural = int((urban_class == 50).sum())
        results["urban_cells"] = n_urban
        results["rural_cells"] = n_rural
    except Exception as exc:
        print(f"  WARNING: GHSL load failed: {exc}", file=sys.stderr)
        print("  Filling urban_class with rural default (50).", file=sys.stderr)
        urban_class = np.full((h, w), 50, dtype=np.int32)

    # 4. Building fraction (Overture Maps, ~1m) — conservative aggregation
    building_frac = None
    if skip_buildings:
        building_frac = np.where(urban_class == 30, 0.6, 0.1).astype(np.float32)
    else:
        try:
            from mal_commonlib.data.loaders.buildings import load_buildings_fraction

            bld_da = load_buildings_fraction(aoi, cache_dir=cache_dir)
            building_frac = aggregate_to_grid(
                bld_da.values,
                bld_da.rio.transform(),
                bld_da.rio.crs,
                target_transform,
                aoi.crs_obj,
                (h, w),
                method="sum",
            )
        except Exception as exc:
            print(f"  WARNING: Building loader failed: {exc}", file=sys.stderr)
            print("  Falling back to urban_class heuristic.", file=sys.stderr)
            building_frac = np.where(urban_class == 30, 0.6, 0.1).astype(np.float32)

    # 5. Wildlife host proxy (WorldCover + JRC GSW + buildings)
    wildlife_proxy = None
    if skip_wildlife:
        wildlife_proxy = np.full((h, w), 0.3, dtype=np.float32)
    else:
        try:
            from mal_commonlib.data.loaders.wildlife import load_wildlife_host_proxy

            wl_da = load_wildlife_host_proxy(aoi, cache_dir=cache_dir)
            wildlife_proxy = aggregate_to_grid(
                wl_da.values,
                wl_da.rio.transform(),
                wl_da.rio.crs,
                target_transform,
                aoi.crs_obj,
                (h, w),
                method="nearest",
            )
        except Exception as exc:
            print(f"  WARNING: Wildlife loader failed: {exc}", file=sys.stderr)
            print("  Using constant 0.3.", file=sys.stderr)
            wildlife_proxy = np.full((h, w), 0.3, dtype=np.float32)

    # 6. Write NetCDF + manifest
    output_dir.mkdir(parents=True, exist_ok=True)
    nc_path = output_dir / f"{aoi.slug}_host_static.nc"
    build_host_static_nc(
        human=human,
        cattle=livestock_totals["cattle"],
        goats=livestock_totals["goats"],
        sheep=livestock_totals["sheep"],
        urban_class=urban_class,
        output_path=nc_path,
        grid_spec=grid_spec,
        pigs=livestock_totals.get("pigs"),
        chickens=livestock_totals.get("chickens"),
        building_fraction=building_frac,
        wildlife_host_proxy=wildlife_proxy,
    )
    manifest_path = write_manifest(
        output_path=nc_path,
        human=human,
        cattle=livestock_totals["cattle"],
        goats=livestock_totals["goats"],
        sheep=livestock_totals["sheep"],
        urban_class=urban_class,
        grid_spec=grid_spec,
        pigs=livestock_totals.get("pigs"),
        chickens=livestock_totals.get("chickens"),
        building_fraction=building_frac,
        wildlife_host_proxy=wildlife_proxy,
    )

    results["nc_path"] = str(nc_path)
    results["manifest_path"] = str(manifest_path)

    # Register in manifest
    register_dataset(
        aoi.slug, "host_static", None,
        str(nc_path.name),
        required_for_abm=True,
        variables=["human", "cattle", "goats", "sheep", "pigs",
                    "chickens", "urban_class", "building_fraction",
                    "wildlife_host_proxy"],
        format="nc",
    )
    register_dataset(
        aoi.slug, "host_manifest", None,
        str(manifest_path.name),
    )

    return results
