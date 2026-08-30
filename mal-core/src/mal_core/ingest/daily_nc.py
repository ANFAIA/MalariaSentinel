"""Daily env NC builder — produces the (time, y, x) NetCDF the C++ ABM reads.

Combines:
  - CHIRPS daily rainfall (mm/day, dims: time, y, x)
  - JRC GSW water occurrence (static, normalized to [0, 1]) -> water_frac
  - ERA5 water temperature (deg C) -> water_temp_c
  - MODIS NDVI (vegetation index, clipped to [0, 1]) -> ndvi
  - SMAP salinity (optional, M7.8) -> salinity_ppt (degree of marine influence)

Optional M12-fix enrichment (when TIF files are present in data_dir):
  - HydroLAKES permanent water mask ({aoi}_permanent_lakes.tif) -> merged
    into water_frac via np.maximum(JRC_GSW, permanent_water)
  - ESA WorldCover wetland mask ({aoi}_wc_wetland.tif) -> diagnostic
    variable (wetland contribution to water_frac is commented-out by default)
  - GSHHG coastline ({aoi}_land_mask.tif) -> saltwater filter.
    JRC cells outside the buffered land mask are dropped from water_frac so
    coastal lagoons are kept but open ocean (where JRC sees permanent surf)
    is rejected. Default buffer 5 km (configurable via
    COASTLINE_BUFFER_M env var). See ``mal_commonlib.data.loaders.coastline``.

Static layers are broadcast to every day (the ABM's daily slice has the same
spatial climate each day; only rainfall changes per day in this version).

Output contract: docs/specs/data/spec.md §6.3, variables matching
mal-core/src/mal_core/abm/include/mal_abm_fast/climate.hpp:80-86.
"""
from __future__ import annotations

import os
import pathlib
import re
from typing import Tuple

import numpy as np
import rasterio
import xarray as xr

NODATA_SENTINEL = -9999.0
WATER_FRAC_VIABILITY_THRESHOLD = 0.05

# Saltwater filter (M12-fix 2026-08-26): cells outside the buffered GSHHG
# land mask are dropped from water_frac. Default 5 km buffer keeps coastal
# lagoons and estuaries while rejecting open ocean (where JRC GSW sees
# permanent surf). Set ``COASTLINE_BUFFER_M=0`` to disable buffering
# (use the raw coastline line), or negative to disable the filter entirely.
COASTLINE_BUFFER_M_DEFAULT = 5_000.0


def read_static_tif(
    path: pathlib.Path, target_shape: Tuple[int, int]
) -> np.ndarray:
    """Read a single-band TIF and return (H, W) float32, nodata -> NaN.

    Resamples bilinearly to ``target_shape`` if the source grid differs.
    """
    with rasterio.open(path) as src:
        nodata = src.nodata
        if (src.height, src.width) == target_shape:
            data = src.read(1).astype(np.float32)
        else:
            from rasterio.enums import Resampling
            data = src.read(
                1,
                out_shape=target_shape,
                resampling=Resampling.bilinear,
            ).astype(np.float32)
        if nodata is not None:
            mask = np.isclose(data, nodata, atol=1.0) | (data == NODATA_SENTINEL)
            data[mask] = np.nan
        return data


def build_daily_env_nc(
    aoi: str,
    data_dir: pathlib.Path,
    output_dir: pathlib.Path | None = None,
    rainfall_file: pathlib.Path | None = None,
    water_frac_file: pathlib.Path | None = None,
    water_temp_file: pathlib.Path | None = None,
    ndvi_file: pathlib.Path | None = None,
    salinity_file: pathlib.Path | None = None,
    dem_file: pathlib.Path | None = None,
) -> dict:
    """Build the daily env NC for an AOI. Returns manifest-ready dict.

    Args:
        aoi: AOI slug (used for output filename and manifest registration).
        data_dir: directory containing the raw input files.
        output_dir: where to write the NC (default: data_dir).
        rainfall_file, water_frac_file, water_temp_file, ndvi_file:
            override input paths (default: conventional filenames in data_dir).
        salinity_file: optional SMAP monthly salinity NC. Defaults to a
            conventional ``{aoi}_salinity_<start>_<end>_monthly.nc`` discovered
            in data_dir. When absent, no ``salinity_ppt`` variable is emitted
            (backward compatible).
        dem_file: optional static DEM GeoTIFF. When present, a static
            ``twi`` variable (Topographic Wetness Index, plan §6.3) is
            computed via ``mal_commonlib.terrain.twi.compute_twi`` and
            embedded in the NC so the C++ pluvial-pool urban rule can gate
            on real terrain data. Defaults to ``{aoi}_elevation.tif``
            (the DEM downloader's manifest output). When absent, no
            ``twi`` variable is emitted (backward compatible).

    Returns:
        dict with 'env_path' (str), 'format' ('nc'), 'aoi_slug', 'n_days',
        'n_viable_cells', and 'grid'.
    """
    data_dir = pathlib.Path(data_dir)
    output_dir = pathlib.Path(output_dir) if output_dir else data_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rain_file = rainfall_file or (
        data_dir / f"{aoi}_rainfall_daily_2024_2025_daily.nc"
        if (data_dir / f"{aoi}_rainfall_daily_2024_2025_daily.nc").exists()
        else _find_chirps_daily(data_dir)
    )
    water_frac_file = water_frac_file or (data_dir / f"{aoi}_water_occurrence.tif")
    year_match = re.search(r"_(20\d{2})(?:_|\.)", rain_file.name)
    data_year = year_match.group(1) if year_match else "2024"
    water_temp_file = water_temp_file or (data_dir / f"{aoi}_water_temp_{data_year}.tif")
    ndvi_file = ndvi_file or (data_dir / f"{aoi}_ndvi_{data_year}.tif")

    for label, p in [
        ("rainfall", rain_file),
        ("water_frac", water_frac_file),
        ("water_temp", water_temp_file),
        ("ndvi", ndvi_file),
    ]:
        if not p.exists():
            raise FileNotFoundError(
                f"{label} input not found: {p}. "
                f"Run: malariasim download --aoi {aoi} --datasets <required>"
            )

    print(f"Reading rainfall: {rain_file}")
    rain_ds = xr.open_dataset(rain_file)
    rainfall_raw = rain_ds.rainfall.values
    times = rain_ds.time.values
    y = rain_ds.y.values
    x = rain_ds.x.values
    n_days, h, w = rainfall_raw.shape
    target_shape = (h, w)

    # Mask rainfall nodata (-9999) with the NEAREST VALID CELL's value for
    # that day (M7.4.1-fix). The old behaviour filled with 0.0, which
    # silently killed the pluvial-pool hydrology wherever ERA5 has gaps —
    # notably the south-eastern coastal strip where Accra sits, leaving
    # cities with synthetic zero rain and no temporary pools.
    # Open ocean (land_mask == 0) still gets 0.0: no pools on the sea.
    rainfall = rainfall_raw.astype(np.float32)
    nodata_mask = rainfall_raw == NODATA_SENTINEL
    nodata_count = int(nodata_mask.sum())
    # Reliable donor cells: filled <50% of days.
    fill_frac = nodata_mask.mean(axis=0)
    valid_cells = fill_frac < 0.5
    if valid_cells.any() and not valid_cells.all():
        from scipy.ndimage import distance_transform_edt
        _, (donor_i, donor_j) = distance_transform_edt(
            ~valid_cells, return_indices=True)
        for d in range(n_days):
            nm = nodata_mask[d]
            if nm.any():
                rainfall[d][nm] = rainfall[d][donor_i[nm], donor_j[nm]]
    elif not valid_cells.any():
        rainfall[nodata_mask] = 0.0  # degenerate: everything filled
    rainfall[rainfall < 0] = 0.0

    # Open ocean -> 0 rain (and the land mask is reused further down for
    # the saltwater filter).
    coastline_file = data_dir / f"{aoi}_land_mask.tif"
    ocean_mask = None
    if coastline_file.exists():
        try:
            lm = read_static_tif(coastline_file, target_shape)
            lm = np.nan_to_num(lm, nan=0.0)
            ocean_mask = lm <= 0.5
            for d in range(n_days):
                rainfall[d][ocean_mask] = 0.0
        except Exception as e:
            print(f"warning: could not read {coastline_file}: {e}")

    # JRC GSW water occurrence -> water_frac (static, broadcast to all days)
    print(f"Reading water_frac: {water_frac_file}")
    water_frac_static = read_static_tif(water_frac_file, target_shape)
    if np.nanmax(water_frac_static) > 1.0:
        water_frac_static = water_frac_static / 100.0
    water_frac_static = np.nan_to_num(water_frac_static, nan=0.0)

    # --- M12-fix saltwater filter (2026-08-26) ---
    # GSHHG coastline -> land_mask. Drop JRC cells outside the buffered
    # land mask so coastal lagoons stay (buffer) but open ocean is rejected.
    # Controlled by the COASTLINE_BUFFER_M env var; negative disables the
    # filter entirely (legacy behaviour, useful for arid landlocked AOIs).
    coastline_file = data_dir / f"{aoi}_land_mask.tif"
    buffer_env = os.environ.get("COASTLINE_BUFFER_M")
    buffer_m = float(buffer_env) if buffer_env is not None else COASTLINE_BUFFER_M_DEFAULT
    coastline_applied = False
    if coastline_file.exists() and buffer_m >= 0:
        print(f"Reading coastline land mask: {coastline_file}")
        land_mask = read_static_tif(coastline_file, target_shape)
        land_mask = np.nan_to_num(land_mask, nan=0.0)
        land_mask = (land_mask > 0.5).astype(np.float32)
        if buffer_m > 0:
            # Buffer is already applied inside the loader when produced via
            # mal_commonlib.data.loaders.coastline.load_coastline_land_mask;
            # here we only dilate if the user explicitly asks for it on a
            # pre-baked file (rare).
            from scipy import ndimage
            cell_size_hint = None
            try:
                cell_size_hint = float(
                    xr.open_dataset(rain_file).attrs.get("resolution_m", 1000.0)
                )
            except Exception:
                cell_size_hint = 1000.0
            radius_cells = max(1, int(np.ceil(buffer_m / cell_size_hint)))
            structure = np.ones((2 * radius_cells + 1, 2 * radius_cells + 1), dtype=bool)
            land_mask = ndimage.binary_dilation(
                land_mask > 0.5, structure=structure
            ).astype(np.float32)
        before = float(water_frac_static.sum())
        water_frac_static = water_frac_static * land_mask
        after = float(water_frac_static.sum())
        print(
            f"Saltwater filter: JRC sum {before:.1f} -> {after:.1f} "
            f"(coastline cells kept: {int(land_mask.sum())} of {land_mask.size})"
        )
        coastline_applied = True
    elif not coastline_file.exists():
        print(
            "WARNING: no land_mask.tif found — saltwater filter "
            "skipped. JRC GSW may include open-ocean cells. "
            "Run: malariasim download --datasets coastline --outputs land_mask"
        )

    # --- M12 enrichment: compose M12 water datasets into water_frac ---
    # Optional layers from hydrolakes / worldcover loaders.  When present
    # they improve the water_frac estimate; when absent the function falls
    # back to JRC GSW only (backward-compatible).
    permanent_water_mask = None
    wetland_mask = None
    component_masks: dict[str, np.ndarray] = {}

    # M12-fix (2026-08-26): if no explicit M12 enrichment is present, derive
    # ``permanent_water_mask`` from the JRC+coast result. Cells that survived
    # the saltwater filter and still have ``water_frac == 1.0`` are
    # JRC-classified permanent water on land. This is what ``env.py`` consumes
    # to classify habitat patches as ``permanent_water`` rather than
    # ``pluvial_pool``. Behaviour matches what the legacy hydrolakes loader
    # produced via JRC GSW threshold >=95%.
    jrc_permanent_water = (water_frac_static >= 1.0).astype(np.float32)
    if permanent_water_mask is None:
        permanent_water_mask = jrc_permanent_water
    else:
        permanent_water_mask = np.maximum(permanent_water_mask, jrc_permanent_water)
    component_masks["jrc_permanent_water"] = jrc_permanent_water.copy()

    lakes_file = data_dir / f"{aoi}_permanent_lakes.tif"
    if lakes_file.exists():
        print(f"Loading M12 permanent water mask: {lakes_file}")
        permanent_water_mask = read_static_tif(lakes_file, target_shape)
        permanent_water_mask = np.nan_to_num(permanent_water_mask, nan=0.0)
        permanent_water_mask = np.clip(permanent_water_mask, 0.0, 1.0)
        component_masks["permanent_lakes"] = permanent_water_mask.copy()

    rivers_file = data_dir / f"{aoi}_permanent_rivers.tif"
    if rivers_file.exists():
        rivers = np.clip(np.nan_to_num(read_static_tif(rivers_file, target_shape), nan=0.0), 0.0, 1.0)
        component_masks["permanent_rivers"] = rivers.copy()
        permanent_water_mask = rivers if permanent_water_mask is None else np.maximum(permanent_water_mask, rivers)

    worldcover_water_file = data_dir / f"{aoi}_wc_permanent_water.tif"
    if worldcover_water_file.exists():
        wc_water = np.clip(np.nan_to_num(read_static_tif(worldcover_water_file, target_shape), nan=0.0), 0.0, 1.0)
        component_masks["worldcover_permanent_water"] = wc_water.copy()
        permanent_water_mask = wc_water if permanent_water_mask is None else np.maximum(permanent_water_mask, wc_water)

    wetland_file = data_dir / f"{aoi}_wc_wetland.tif"
    if wetland_file.exists():
        print(f"Loading M12 wetland mask: {wetland_file}")
        wetland_mask = read_static_tif(wetland_file, target_shape)
        wetland_mask = np.nan_to_num(wetland_mask, nan=0.0)
        wetland_mask = np.clip(wetland_mask, 0.0, 1.0)

    # Merge: permanent water always has water_frac = 1.0
    if permanent_water_mask is not None:
        water_frac_static = np.maximum(water_frac_static, permanent_water_mask)
    # Optionally add wetland contribution (uncomment to enable)
    # if wetland_mask is not None:
    #     water_frac_static = np.clip(water_frac_static + 0.3 * wetland_mask, 0.0, 1.0)

    water_frac = np.broadcast_to(water_frac_static, (n_days, h, w)).copy()
    n_viable = int((water_frac_static > WATER_FRAC_VIABILITY_THRESHOLD).sum())
    if n_viable == 0:
        raise RuntimeError(
            f"CRITICAL: 0 viable habitat patches for AOI '{aoi}'! "
            f"water_frac is all <= {WATER_FRAC_VIABILITY_THRESHOLD}. "
            f"Check {water_frac_file} contains real JRC GSW data."
        )

    def _annual_raster_stack(prefix: str, fallback: pathlib.Path, fill: float) -> np.ndarray:
        """Use matching annual rasters for each day, with explicit fallback."""
        years = np.unique(times.astype("datetime64[Y]")).astype(int) + 1970
        annual: dict[int, np.ndarray] = {}
        for data_year in years:
            candidate = data_dir / f"{aoi}_{prefix}_{data_year}.tif"
            path = candidate if candidate.exists() else fallback
            print(f"Reading {prefix}: {path}")
            annual[int(data_year)] = np.nan_to_num(
                read_static_tif(path, target_shape), nan=fill,
            )
        stacked = np.empty((n_days, h, w), dtype=np.float32)
        for index, timestamp in enumerate(times):
            data_year = int(timestamp.astype("datetime64[Y]").astype(int) + 1970)
            stacked[index] = annual[data_year]
        return stacked

    # ERA5 water temperature and MODIS NDVI are annual static rasters.
    water_temp_c = _annual_raster_stack("water_temp", water_temp_file, 25.0)
    ndvi = np.clip(_annual_raster_stack("ndvi", ndvi_file, 0.5), 0.0, 1.0)

    # SMAP monthly sea surface salinity -> salinity_ppt (M7.8), optional.
    # Reproject each month to the AOI grid, mask land/no-data cells to 0.0
    # (freshwater), and broadcast the monthly value to every day of that month.
    # Absent file -> no salinity_ppt variable at all (backward compatible).
    salinity_monthly = None
    salinity_ppt = None
    salinity_path = salinity_file or _find_salinity_monthly(data_dir)
    if salinity_path is not None and salinity_path.exists():
        print(f"Reading salinity (monthly): {salinity_path}")
        salinity_monthly = _read_salinity_monthly(salinity_path, y, x, _env_crs(rain_ds))
    if salinity_monthly is not None:
        salinity_ppt = np.zeros((n_days, h, w), dtype=np.float32)
        for index, timestamp in enumerate(times):
            month_key = timestamp.astype("datetime64[M]").astype("datetime64[D]")
            arr = salinity_monthly.get(month_key)
            if arr is not None:
                # Cells without SMAP data (land, fill, mission gap) -> freshwater 0.0.
                salinity_ppt[index] = np.nan_to_num(arr, nan=0.0)

    # --- M7.4.1: static TWI from DEM (plan §6.3 pluvial-pool rules) ------
    # Embedded as a single-plane ('y', 'x') variable so the C++ env reader
    # can gate the urban dynamic-pool rule on real terrain. Discovery
    # follows the DEM downloader manifest output ({aoi}_elevation.tif).
    dem_file = dem_file or (data_dir / f"{aoi}_elevation.tif")
    twi_static: np.ndarray | None = None
    if dem_file.exists():
        from mal_commonlib.terrain.twi import compute_twi

        print(f"Computing TWI from DEM: {dem_file}")
        dem_arr = read_static_tif(dem_file, target_shape)
        dem_arr = dem_arr.astype(np.float32)
        dem_arr[dem_arr <= NODATA_SENTINEL + 1] = np.nan
        dem_da = xr.DataArray(
            dem_arr, dims=("y", "x"), coords={"y": y, "x": x}
        )
        # x/y coords are in degrees (EPSG:4326) for regional AOIs:
        # convert the median degree step to metres (equatorial latitude).
        deg_step = float(np.median(np.abs(np.diff(x))))
        cell_size_m = deg_step * 111_320.0 if deg_step > 0 else 1000.0
        twi_da = compute_twi(dem_da, cell_size_m=cell_size_m)
        twi_static = np.asarray(twi_da.values, dtype=np.float32)
        twi_static = np.nan_to_num(twi_static, nan=0.0)
        twi_static[twi_static < 0.0] = 0.0
        print(
            f"TWI: min={twi_static.min():.2f} mean={twi_static.mean():.2f} "
            f"max={twi_static.max():.2f} | cells TWI>7: "
            f"{int((twi_static > 7.0).sum())} of {twi_static.size}"
        )
    else:
        print(
            f"WARNING: no DEM found ({dem_file}) — no 'twi' variable in the "
            "env NC; the urban pluvial-pool rule will fall back to "
            "rain + building-cover gating (no terrain gate)."
        )

    # --- M7.4.1: static per-cell larval→adult capacity multiplier ---------
    # Literature-anchored (see papers/anopheles-dynamics/depinay-2004-*,
    # papers/anopheles-dynamics/costantini-1996-*, KB notes):
    #   * Adult equilibrium per m² of productive water:
    #       E_daily × τ_adult = 0.143 × 9.3 ≈ 1.33 adults/m²
    #     E_daily = 0.143/m²/d is the midpoint of field emergence traps
    #     (0.74-1.8 An. gambiae s.l. adults/m²/week: Ndenga/Fillinger 2011
    #     PLoS ONE; Fillinger 2009 Malar J 8:62 Gambia).
    #     τ_adult = 9.3 d (basal survival 0.95/d @27.5 °C; MRR field range
    #     4.5-14.3 d: Costantini 1996; Diallo 2026).
    #   * Biomass cross-check (Depinay 2004 K = L_Max·S, L_Max = 300 mg/m²;
    #     Bomblies 2008: 300→30 mg/m² seasonal): 300-600 larvae/m² ×
    #     1.8-6.8% egg→adult × (τ/T_larva) ≈ 1.2 adults/m²/week — converges.
    #   * Permanent water (JRC=1.0) is margin-productive only:
    #     f_shallow = 0.10 of the cell water area (littoral strips).
    #     Temporary/rain pools are fully productive (f_shallow = 1.0).
    #   * Urban cells without standing water get a pluvial-pool water
    #     proxy (2% of cell × (1 − 0.5·building_fraction)): urban pools
    #     are as or more productive per m² than natural ones (Accra
    #     13.7 larvae/dip; Kumasi urban agriculture >80% of city mosquitoes).
    #   * f_NDVI: tent peaked at NDVI 0.4-0.6 (optimum band; dominant
    #     suitability predictor with ~2-week lag in field studies).
    # The NC carries `k_capacity_mult` = K_abs / K_MAX_C(m=1000) so the
    # C++ Beverton-Holt larval cap K_patch = K_MAX × K_eff picks it up
    # via the existing per-cell K_eff view.
    K_E_DAILY = 0.143
    K_TAU_ADULT_D = 9.3
    K_A_CELL_M2 = 1.0e6
    K_SHALLOW_PERMANENT = 0.10
    K_URBAN_POOL_FRAC = 0.02
    K_MAX_C = 1000.0

    ndvi_mean = ndvi.mean(axis=0) if ndvi.ndim == 3 else ndvi

    # Static urban structure (from the host dataset): building_fraction
    # and GHS-SMOD urban_class drive the urban pluvial-pool proxy and
    # the building cover reduction of effective water area.
    bldg_static = np.zeros((h, w), dtype=np.float32)
    urban_class_static = np.zeros((h, w), dtype=np.int32)
    hosts_nc = data_dir / f"{aoi}_host_static.nc"
    if hosts_nc.exists():
        hds = xr.open_dataset(hosts_nc)
        if "building_fraction" in hds:
            bldg_static = np.asarray(
                hds["building_fraction"].squeeze(), dtype=np.float32
            )
        if "urban_class" in hds:
            urban_class_static = np.asarray(
                hds["urban_class"].squeeze()
            ).astype(np.int32)
        hds.close()
    else:
        print(
            "WARNING: no host_static.nc found — k_capacity_mult computed "
            "without urban modifiers (buildings/urban pools)."
        )

    def _f_ndvi(v: np.ndarray) -> np.ndarray:
        f = np.full_like(v, 0.3, dtype=np.float32)
        rising = (v >= 0.2) & (v < 0.4)
        f[rising] = 0.3 + 0.7 * (v[rising] - 0.2) / 0.2
        f[(v >= 0.4) & (v <= 0.6)] = 1.0
        falling = (v > 0.6) & (v <= 0.8)
        f[falling] = 1.0 - 0.6 * (v[falling] - 0.6) / 0.2
        f[v > 0.8] = 0.4
        return f

    if permanent_water_mask is not None:
        perm = np.asarray(permanent_water_mask) > 0.5
    else:
        perm = water_frac_static >= 1.0
    f_urban_water = 1.0 - 0.5 * np.clip(bldg_static, 0.0, 1.0)

    water_eff = water_frac_static * _f_ndvi(ndvi_mean) * f_urban_water
    water_eff = np.where(perm, water_eff * K_SHALLOW_PERMANENT, water_eff)

    # Urban pluvial-pool proxy: built-up cells with no standing water
    # still produce rain pools after storms (drainage, tyre tracks,
    # construction sites).
    urban_no_water = (
        (urban_class_static == 30) if urban_class_static is not None
        else np.zeros_like(water_frac_static, dtype=bool)
    ) & (water_frac_static < 0.05) & (bldg_static >= 0.05)
    urban_water_proxy = (
        K_URBAN_POOL_FRAC
        * (1.0 - 0.5 * np.clip(bldg_static, 0.0, 1.0))
        * _f_ndvi(ndvi_mean)
    )
    water_eff = np.where(urban_no_water, urban_water_proxy, water_eff)

    k_abs = K_E_DAILY * K_TAU_ADULT_D * K_A_CELL_M2 * water_eff
    k_capacity_mult = (k_abs / K_MAX_C).astype(np.float32)
    k_capacity_mult = np.clip(k_capacity_mult, 0.0, 500.0)  # sane cap
    n_k_cells = int((k_capacity_mult >= 1.0).sum())
    print(
        "k_capacity_mult: cells with K>=1000 adults: "
        f"{n_k_cells}; median K on habitat cells: "
        f"{float(np.median(k_capacity_mult[k_capacity_mult > 0]) * K_MAX_C):.0f}"
    )

    ds = xr.Dataset(
        {
            "water_frac": (["time", "y", "x"], water_frac,
                           {"long_name": "Enriched water fraction (JRC GSW + M12 permanent water)",
                            "units": "1"}),
            "rainfall": (["time", "y", "x"], rainfall,
                         {"long_name": "CHIRPS v2.0 daily precipitation",
                          "units": "mm/day"}),
            "water_temp_c": (["time", "y", "x"], water_temp_c,
                             {"long_name": "ERA5-Land 2m temperature (daily mean)",
                              "units": "degC"}),
            "ndvi": (["time", "y", "x"], ndvi,
                     {"long_name": "MODIS NDVI", "units": "1"}),
        },
        coords={"time": times, "y": y, "x": x},
        attrs={
            "Conventions": "CF-1.8",
            "title": f"MalariaSentinel daily env tensor — {aoi}",
            "aoi_slug": aoi,
            "scale": "regional",
            "contract_version": "2.0",
            "generator_version": "m2-daily-0.5.0",
            "m12_enriched": int(permanent_water_mask is not None or wetland_mask is not None),
        },
    )
    if salinity_ppt is not None:
        ds["salinity_ppt"] = (
            ["time", "y", "x"], salinity_ppt,
            {"long_name": "SMAP RSS L3 monthly sea surface salinity (broadcast)",
             "units": "psu"},
        )
    # M12 component masks: one NC variable per contributing source
    # (e.g. m12_jrc_permanent_water, m12_permanent_lakes, m12_permanent_rivers,
    #  m12_worldcover_permanent_water). Currently Ghana only contributes
    # jrc_permanent_water; the others activate when their TIFs land. These
    # are diagnostic — the C++ ABM reader does not consume them today.
    for name, component in component_masks.items():
        ds[f"m12_{name}"] = (
            ["time", "y", "x"], np.broadcast_to(component, (n_days, h, w)).copy(),
            {"long_name": f"M12 {name} mask", "units": "1"},
        )

    # Canonical permanent water mask — the one the ABM actually consumes.
    # Built from the union of all M12 component masks (max() across sources)
    # so adding HydroLAKES / WorldCover enrichment is additive and backward
    # compatible.
    if permanent_water_mask is not None:
        pw_broadcast = np.broadcast_to(permanent_water_mask, (n_days, h, w)).copy()
        ds["permanent_water_mask"] = (
            ["time", "y", "x"], pw_broadcast,
            {"long_name": "Permanent water mask (union of M12 component sources)", "units": "1"},
        )


    if wetland_mask is not None:
        wl_broadcast = np.broadcast_to(wetland_mask, (n_days, h, w)).copy()
        ds["wetland_mask"] = (
            ["time", "y", "x"], wl_broadcast,
            {"long_name": "Wetland mask (ESA WorldCover class 90)", "units": "1"},
        )

    if twi_static is not None:
        ds["twi"] = (
            ["y", "x"], twi_static,
            {"long_name": "Topographic Wetness Index (static, from DEM)",
             "units": "1"},
        )

    ds["k_capacity_mult"] = (
        ["y", "x"], k_capacity_mult,
        {"long_name": "Per-cell adult capacity multiplier "
                      "(K_patch = K_MAX * mult; literature-anchored: "
                      "emergence 0.143/m2/d x tau 9.3 d x water area "
                      "x NDVI/urban/shallow modifiers)",
         "units": "1"},
    )

    # Core variables are always written with zlib; diagnostic vars too
    encoding_vars = ["water_frac", "rainfall", "water_temp_c", "ndvi"]
    if salinity_ppt is not None:
        encoding_vars.append("salinity_ppt")
    if permanent_water_mask is not None:
        encoding_vars.append("permanent_water_mask")
    if wetland_mask is not None:
        encoding_vars.append("wetland_mask")
    if twi_static is not None:
        encoding_vars.append("twi")
    encoding_vars.append("k_capacity_mult")

    encoding = {v: {"dtype": "float32", "zlib": True, "complevel": 4}
                for v in encoding_vars}

    years_in_data = np.unique(times.astype("datetime64[Y]")).astype(int) + 1970
    output_path = output_dir / f"{aoi}_regional_{years_in_data.min()}_{years_in_data.max()}_env.nc"
    print(f"Writing: {output_path}")
    ds.to_netcdf(output_path, encoding=encoding)

    print(
        f"\n=== SUMMARY ===\n"
        f"  water_frac: [{water_frac.min():.4f}, {water_frac.max():.4f}], "
        f"viable cells (>0.05): {n_viable}\n"
        f"  M12 enrichment: permanent_water={'yes' if permanent_water_mask is not None else 'no'}, "
        f"wetland={'yes' if wetland_mask is not None else 'no'}\n"
        f"  rainfall: [{rainfall.min():.1f}, {rainfall.max():.1f}], "
        f"nodata replaced: {nodata_count}\n"
        f"  water_temp: [{water_temp_c.min():.1f}, {water_temp_c.max():.1f}]\n"
        f"  ndvi: [{ndvi.min():.2f}, {ndvi.max():.2f}]"
    )

    # Manifest variable list: core ABM variables always present; M12 diagnostics
    # are optional (C++ reader ignores them, but they're useful for analysis).
    variables = ["water_frac", "rainfall", "water_temp_c", "ndvi"]
    if salinity_ppt is not None:
        variables.append("salinity_ppt")
    if permanent_water_mask is not None:
        variables.append("permanent_water_mask")
    if wetland_mask is not None:
        variables.append("wetland_mask")

    return {
        "env_path": str(output_path),
        "format": "nc",
        "aoi_slug": aoi,
        "n_days": n_days,
        "n_viable_cells": n_viable,
        "grid": f"{h}x{w}",
        "variables": variables,
        "m12_enriched": permanent_water_mask is not None or wetland_mask is not None,
    }


def _find_salinity_monthly(data_dir: pathlib.Path) -> pathlib.Path | None:
    """Locate the SMAP monthly salinity NC by conventional glob fallback."""
    candidates = sorted(data_dir.glob(f"*salinity*monthly*.nc"))
    if candidates:
        return candidates[0]
    candidates = sorted(data_dir.glob("*salinity*.nc"))
    return candidates[0] if candidates else None


def _env_crs(rain_ds: xr.Dataset) -> str:
    """CRS of the env grid, read from the rainfall NC (fallback EPSG:4326)."""
    try:
        crs = rain_ds.rio.crs
        if crs is not None:
            return str(crs)
    except Exception:  # noqa: BLE001 — no rioxarray CRS attached
        pass
    return "EPSG:4326"


def _reference_grid(y: np.ndarray, x: np.ndarray, crs: str) -> xr.DataArray:
    """1-pixel reference DataArray covering the env (y, x) grid in ``crs``."""
    h, w = len(y), len(x)
    transform = rasterio.transform.from_bounds(x.min(), y.min(), x.max(), y.max(), w, h)
    arr = np.zeros((h, w), dtype=np.float32)
    ref = xr.DataArray(arr, dims=("y", "x"), coords={"y": y, "x": x})
    ref.rio.write_crs(crs, inplace=True)
    ref.rio.write_transform(transform, inplace=True)
    return ref


def _read_salinity_monthly(
    path: pathlib.Path, y: np.ndarray, x: np.ndarray, crs: str
) -> dict[np.datetime64, np.ndarray]:
    """Read a SMAP monthly salinity NC, reproject each month to the env grid.

    Returns ``{month_start_day_precision: (H, W) float32}`` mapping, one entry
    per month in the file. Land / no-data cells are left as NaN so the caller
    can decide the freshwater (0.0) replacement.
    """
    resampling = rasterio.enums.Resampling.bilinear
    ref = _reference_grid(y, x, crs)
    out: dict[np.datetime64, np.ndarray] = {}
    with xr.open_dataset(path) as ds:
        if "salinity" not in ds:
            raise ValueError(
                f"salinity NC {path} has no 'salinity' variable; "
                f"vars={sorted(ds.data_vars)}"
            )
        sss = ds["salinity"]
        # SMAP is always WGS-84; the runner embeds CRS via rioxarray, but
        # guard against a file written without a spatial_ref coordinate.
        if sss.rio.crs is None:
            sss.rio.write_crs("EPSG:4326", inplace=True)
        times = ds.time.values
        for i in range(int(sss.sizes["time"])):
            month_da = sss.isel(time=i, drop=True)
            rep = month_da.rio.reproject_match(ref, resampling=resampling)
            arr = np.asarray(rep.values, dtype=np.float32)
            key = np.datetime64(str(times[i])[:10], "D")
            out[key] = arr
    return out


def _find_chirps_daily(data_dir: pathlib.Path) -> pathlib.Path:
    """Locate the CHIRPS daily NC by glob fallback."""
    candidates = sorted(data_dir.glob("*rainfall_daily*.nc"))
    if not candidates:
        raise FileNotFoundError(
            f"No CHIRPS daily rainfall NC found in {data_dir}. "
            f"Run: malariasim download --aoi <slug> --datasets chirps "
            f"--outputs rainfall_daily --years 2024,2025"
        )
    return candidates[0]
