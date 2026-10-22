"""Daily env NC builder — produces the (time, y, x) NetCDF the C++ ABM reads.

Contract v3.0 of the proxy-habitat redesign
(docs/plans/in-process/redesign/02-oferta-criaderos-proxies-download-ingest-abm.md
§8-§9). The NC carries:

DAILY variables (dims: time, y, x)
  - ``rainfall``    CHIRPS v2.0 daily precipitation (mm/day)
  - ``air_temp_c``  ERA5-Land 2 m daily mean temperature (°C — the channel
                    is named for what it actually measures; the retired
                    annual ``water_temp_c`` TIF stack is NOT read)
  - ``salinity_ppt`` SMAP monthly sea-surface salinity broadcast to days
                    (optional, M7.8)

STATIC variables (dims: y, x) — the six-habitat feature contract; nothing
here is recomputed per year and nothing is broadcast into daily bands:
  - ``jrc_persistent``      JRC GSW fraction of >=80 %-occurrence water
  - ``lc_built``            Dynamic World built fraction (label 6, mode-of-year)
  - ``lc_wetland``          Dynamic World flooded_vegetation fraction (label 3)
  - ``lc_open_plus_water``  DW grass+shrub+bare+water fraction (labels 2/5/7/0)
  - ``lc_crop``             Dynamic World crops fraction (label 4)

Retention: the full daily rainfall/temperature series available at build
time is written WHOLE — days before the simulation start are the causal
warm-up window the C++ coordinator integrates the pluvial state (z) over
(never per-species, never re-derived from annual data).

Removed with the v2 contract: ``water_frac`` daily band, ``ndvi`` daily
band, ``twi``/``catchment_ratio`` statics, ``k_capacity_mult`` element
(already moved to Python ``mal_core.habitat``), ``permanent_water_mask``
/ ``wetland_mask``/ m12 component masks and the OpenM12 enrichment path.
"""
from __future__ import annotations

import os
import pathlib
from typing import Tuple

import numpy as np
import rasterio
import xarray as xr

from ..habitat.config import CONFIG as _MODEL_CONSTANTS

_INGEST = _MODEL_CONSTANTS["ingest"]

_ENV_NC = str(_MODEL_CONSTANTS["contracts"]["env_nc"])

NODATA_SENTINEL = float(_INGEST["nodata_sentinel"])

# Saltwater filter (M12-fix 2026-08-26; preserved): cells outside the buffered
# GSHHG land mask are dropped from the static JRC feature. Default 5 km
# buffer keeps coastal lagoons and estuaries while rejecting open ocean (where
# JRC GSW sees permanent surf). Set ``COASTLINE_BUFFER_M=0`` to disable
# buffering, negative to disable the filter entirely.
COASTLINE_BUFFER_M_DEFAULT = float(_INGEST["coastline_buffer_m"])

# Candidate-cell floor: cells whose total potential (sum of the six H
# features, computed by mal_core.habitat.potential) is below this are
# outside the ABM patch union. Values live in model_constants.yaml
# (ingest.candidate_min_ingest); the engine's patch floor is a separate
# key (habitat.candidate_min_engine) with a different role.
HABITAT_CANDIDATE_MIN = float(_INGEST["candidate_min_ingest"])

# --- consumer dependency table (the ONLY dataset knowledge in this file) ------
#
# Identity of every input is its manifest key; resolution happens entirely
# through mal_core.download.catalog (manifest.json = single source of truth).
# Legacy conventional-name fallbacks do NOT live here — dirs that predate
# manifests are migrated once with catalog.register_existing().

from ..download import catalog as _cat

ENV_INPUT_SLOTS: dict[str, _cat.Slot] = {
    # Required by the builder — absent from the manifest = hard error.
    "rainfall": _cat.Slot("chirps_rainfall_daily"),
    "air_temp": _cat.Slot("era5_air_temp_daily"),
    "jrc_features": _cat.Slot("jrc_habitat_features"),
    "wc_fractions": _cat.Slot("dw_class_fractions"),
    # Optional — absent entry emits a warning and the corresponding
    # variable/behaviour is skipped (backward-compatible).
    "land_mask": _cat.Slot("coastline_land_mask", required=False),
    "host_static": _cat.Slot("host_static", required=False),
    "salinity": _cat.Slot("smap_salinity", required=False),
}


def resolve_daily_env_inputs(
    aoi: str,
    data_dir: pathlib.Path,
    *,
    explicit: dict | None = None,
) -> dict[str, dict]:
    """Resolve (only) every input ``build_daily_env_nc`` consumes — no build.

    The build-free counterpart used to verify manifest wiring: required
    slots must resolve to an existing file or the call raises; optional
    slots with no manifest entry are simply absent.
    """
    resolved = _cat.resolve_inputs(
        aoi, ENV_INPUT_SLOTS, data_dir=pathlib.Path(data_dir),
        explicit=explicit,
    )
    out: dict[str, dict] = {}
    for slot_name, value in resolved.items():
        if value is None:
            continue
        out[slot_name] = {"path": value, "source": "manifest"}
    return out



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
    air_temp_file: pathlib.Path | None = None,
    jrc_features_file: pathlib.Path | None = None,
    wc_fractions_file: pathlib.Path | None = None,
    salinity_file: pathlib.Path | None = None,
) -> dict:
    """Build the daily env NC for an AOI. Returns manifest-ready dict.

    Args:
        aoi: AOI slug (used for output filename and manifest registration).
        data_dir: directory containing the raw input files.
        output_dir: where to write the NC (default: data_dir).
        All other args: explicit input overrides. By default every input
            resolves from the manifest via ``ENV_INPUT_SLOTS`` — required
            slots hard-error when missing.

    Returns:
        dict with 'env_path' (str), 'format' ('nc'), 'aoi_slug', 'n_days',
        'n_candidate_cells' and 'grid'.
    """
    data_dir = pathlib.Path(data_dir)
    output_dir = pathlib.Path(output_dir) if output_dir else data_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    explicit = {
        name: p for name, p in (
            ("rainfall", rainfall_file),
            ("air_temp", air_temp_file),
            ("jrc_features", jrc_features_file),
            ("wc_fractions", wc_fractions_file),
            ("salinity", salinity_file),
        ) if p is not None
    }
    resolved = _cat.resolve_inputs(
        aoi, ENV_INPUT_SLOTS, data_dir=data_dir, explicit=explicit
    )
    rain_file = resolved["rainfall"]
    air_temp_path = resolved["air_temp"]
    jrc_features_path = resolved["jrc_features"]
    wc_fractions_path = resolved["wc_fractions"]
    coastline_file = resolved["land_mask"]

    # --- daily rainfall (CHIRPS) -----------------------------------------
    print(f"Reading rainfall: {rain_file}")
    rain_ds = xr.open_dataset(rain_file)
    rainfall_raw = rain_ds.rainfall.values
    times = rain_ds.time.values
    y = rain_ds.y.values
    x = rain_ds.x.values
    n_days, h, w = rainfall_raw.shape
    target_shape = (h, w)

    # Mask rainfall nodata (-9999) with the NEAREST VALID CELL's value for
    # that day (M7.4.1-fix preserved).  Open ocean (land_mask == 0) gets 0.0.
    rainfall = rainfall_raw.astype(np.float32)
    nodata_mask = rainfall_raw == NODATA_SENTINEL
    nodata_count = int(nodata_mask.sum())
    fill_frac = nodata_mask.mean(axis=0)
    valid_cells = fill_frac < float(_INGEST["fill_frac_valid_max"])
    if valid_cells.any() and not valid_cells.all():
        from scipy.ndimage import distance_transform_edt
        _, (donor_i, donor_j) = distance_transform_edt(
            ~valid_cells, return_indices=True)
        for d in range(n_days):
            nm = nodata_mask[d]
            if nm.any():
                rainfall[d][nm] = rainfall[d][donor_i[nm], donor_j[nm]]
    elif not valid_cells.any():
        rainfall[nodata_mask] = 0.0
    rainfall[rainfall < 0] = 0.0

    ocean_mask = None
    if coastline_file is not None:
        try:
            lm = read_static_tif(coastline_file, target_shape)
            lm = np.nan_to_num(lm, nan=0.0)
            ocean_mask = lm <= float(_INGEST["ocean_mask_threshold"])
            for d in range(n_days):
                rainfall[d][ocean_mask] = 0.0
        except Exception as e:
            print(f"warning: could not read {coastline_file}: {e}")

    # --- daily air temperature (ERA5-Land) --------------------------------
    # Contract v3.0: real daily series with its own time axis. The NC's
    # timeframe must CONTAIN the rainfall timeframe (the download contract
    # guarantees years alignment); otherwise the build fails loudly — the
    # retired annual-TIF→daily-broadcast path is gone.
    print(f"Reading air temperature: {air_temp_path}")
    at_ds = xr.open_dataset(air_temp_path)
    if "air_temp_c" not in at_ds:
        raise ValueError(
            f"era5_air_temp_daily NC {air_temp_path} has no 'air_temp_c' "
            f"variable; vars={sorted(at_ds.data_vars)}"
        )
    air_temp_c = at_ds["air_temp_c"].values.astype(np.float32)
    at_times = at_ds.time.values.astype("datetime64[D]")
    env_days = times.astype("datetime64[D]")
    missing = [str(d) for d in env_days if d not in set(at_times)]
    if missing:
        raise ValueError(
            f"era5_air_temp_daily NC does not cover {len(missing)} env days, "
            f"first absent: {missing[0]}. "
            f"Re-run: malariasim download --datasets era5 --outputs air_temp_daily"
        )
    at_index = {str(t): i for i, t in enumerate(at_times)}
    # NOTE: re-index via lookup for robustness against non-contiguous axes.
    air_temp_c = np.stack(
        [air_temp_c[at_index[str(d)]]
         for d in env_days], axis=0
    ).astype(np.float32)
    if ocean_mask is not None:
        for d in range(n_days):
            air_temp_c[d][ocean_mask] = 0.0

    # --- static habitat features ------------------------------------------
    def _static_from_ds(path, var_names: tuple[str, ...]) -> dict[str, np.ndarray]:
        with xr.open_dataset(path) as ds_ref:
            out = {}
            for v in var_names:
                if v not in ds_ref:
                    raise ValueError(
                        f"{path} has no '{v}' variable; "
                        f"vars={sorted(ds_ref.data_vars)}"
                    )
                arr = ds_ref[v].values.astype(np.float32)
                if arr.ndim == 3:
                    # Dynamic World per-year stack (option A): mean of the
                    # per-year areal fractions = the single static plane.
                    arr = arr.mean(axis=0, dtype=np.float32)
                if arr.ndim != 2 or arr.shape != (h, w):
                    raise ValueError(
                        f"{path}.{v} shape {arr.shape} != env grid {(h, w)}"
                    )
                out[v] = np.nan_to_num(arr, nan=0.0)
        return out

    print(f"Reading JRC habitat features: {jrc_features_path}")
    jrc = _static_from_ds(
        jrc_features_path, ("jrc_persistent",)
    )
    print(f"Reading Dynamic World class fractions: {wc_fractions_path}")
    wc = _static_from_ds(
        wc_fractions_path,
        ("lc_built", "lc_wetland", "lc_open_plus_water", "lc_crop"),
    )

    # --- M12-fix saltwater filter on the static JRC signal (preserved) ----
    buffer_env = os.environ.get("COASTLINE_BUFFER_M")
    buffer_m = float(buffer_env) if buffer_env is not None else COASTLINE_BUFFER_M_DEFAULT
    if coastline_file is not None and buffer_m >= 0:
        print(f"Reading coastline land mask: {coastline_file}")
        land_mask = read_static_tif(coastline_file, target_shape)
        land_mask = np.nan_to_num(land_mask, nan=0.0)
        land_mask = (land_mask > float(_INGEST["land_mask_threshold"])).astype(np.float32)
        if buffer_m > 0:
            from scipy import ndimage
            cell_size_hint = float(_INGEST["cell_size_hint_m"])
            try:
                cell_size_hint = float(
                    rain_ds.attrs.get("resolution_m",
                                      float(_INGEST["cell_size_hint_m"])))
            except Exception:
                pass
            radius_cells = max(int(_INGEST["min_dilation_radius_cells"]),
                               int(np.ceil(buffer_m / cell_size_hint)))
            structure = np.ones((2 * radius_cells + 1, 2 * radius_cells + 1), dtype=bool)
            land_mask = ndimage.binary_dilation(
                land_mask > 0.5, structure=structure
            ).astype(np.float32)
        before = float(jrc["jrc_persistent"].sum())
        jrc["jrc_persistent"] *= land_mask
        after = float(jrc["jrc_persistent"].sum())
        print(
            f"Saltwater filter: JRC persistent sum {before:.1f} -> {after:.1f} "
            f"(coastline cells kept: {int(land_mask.sum())} of {land_mask.size})"
        )
    else:
        warning = (
            "no land_mask.tif found — saltwater filter skipped; JRC GSW "
            "may include open-ocean cells."
        )
        print(("disabled by COASTLINE_BUFFER_M<0" if coastline_file is not None
               else "WARNING: ") + warning
              if coastline_file is None else
              f"note: {warning} (filter disabled)")

    # --- candidate-cell census (pure statics, no DEM, no NDVI thresholds) --
    from mal_core.habitat import potential as _pot
    h_static = _pot.static_potential({**jrc, **wc})
    h_total = np.asarray(_pot.total_potential(h_static), dtype=np.float32)
    candidate = h_total > HABITAT_CANDIDATE_MIN
    n_candidates = int(candidate.sum())
    if n_candidates == 0:
        raise RuntimeError(
            f"CRITICAL: 0 candidate habitat cells for AOI '{aoi}' — the "
            "static habitat potential is empty. Check the "
            "jrc_habitat_features / dw_class_fractions files."
        )

    # --- optional SMAP monthly salinity (M7.8) -----------------------------
    salinity_monthly = None
    salinity_ppt = None
    if resolved["salinity"] is not None:
        salinity_monthly = _read_salinity_monthly(
            resolved["salinity"], y, x, _env_crs(rain_ds))
    if salinity_monthly is not None:
        salinity_ppt = np.zeros((n_days, h, w), dtype=np.float32)
        for index, timestamp in enumerate(times):
            month_key = timestamp.astype("datetime64[M]").astype("datetime64[D]")
            arr = salinity_monthly.get(month_key)
            if arr is not None:
                salinity_ppt[index] = np.nan_to_num(arr, nan=0.0)

    # --- assemble -----------------------------------------------------------
    ds = xr.Dataset(
        {
            "rainfall": (["time", "y", "x"], rainfall,
                         {"long_name": "CHIRPS v2.0 daily precipitation",
                          "units": "mm/day"}),
            "air_temp_c": (["time", "y", "x"], air_temp_c,
                           {"long_name": "ERA5-Land 2m temperature (daily mean)",
                            "units": "degC"}),
            "jrc_persistent": (["y", "x"], jrc["jrc_persistent"],
                               {"long_name": "JRC GSW fraction of >=80%-occurrence "
                                             "water pixels (static)",
                                "units": "1"}),
            "lc_built": (["y", "x"], wc["lc_built"],
                         {"long_name": "Dynamic World built fraction "
                                       "(class 50, static)", "units": "1"}),
            "lc_wetland": (["y", "x"], wc["lc_wetland"],
                           {"long_name": "Dynamic World flooded-vegetation fraction "
                                         "fraction (classes 90,95, static)",
                            "units": "1"}),
            "lc_open_plus_water": (
                ["y", "x"], wc["lc_open_plus_water"],
                {"long_name": "Dynamic World open+water fraction "
                              "fraction (classes 30,20,60,100,80, static)",
                 "units": "1"}),
            "lc_crop": (["y", "x"], wc["lc_crop"],
                        {"long_name": "Dynamic World crops fraction "
                                      "(class 40, static)", "units": "1"}),
        },
        coords={"time": times, "y": y, "x": x},
        attrs={
            "Conventions": "CF-1.8",
            "title": f"MalariaSentinel daily env tensor — {aoi}",
            "aoi_slug": aoi,
            "scale": "regional",
            "contract_version": _ENV_NC,
            "generator_version": "proxy-habitat-v1-0.1.0",
            "n_candidate_cells": int(n_candidates),
        },
    )
    if salinity_ppt is not None:
        ds["salinity_ppt"] = (
            ["time", "y", "x"], salinity_ppt,
            {"long_name": "SMAP RSS L3 monthly sea surface salinity (broadcast)",
             "units": "psu"},
        )

    encoding = {
        v: {"dtype": "float32", "zlib": True,
            "complevel": int(_INGEST["nc_compression_level"])}
        for v in ds.data_vars
    }

    years_in_data = np.unique(times.astype("datetime64[Y]")).astype(int) + 1970
    output_path = output_dir / f"{aoi}_regional_{years_in_data.min()}_{years_in_data.max()}_env.nc"
    # CF-compliant georeferencing (preserved from v2): explicit lat/lon
    # coordinate variables + grid_mapping (crs) so older GDAL netCDF
    # drivers expose the 2-D static variables as SUBDATASETS.
    y_m = float(np.median(np.abs(np.diff(y)))) if len(y) > 1 else 0.0
    x_m = float(np.median(np.abs(np.diff(x)))) if len(x) > 1 else 0.0
    step_max = int(_INGEST["grid_degrees_step_max"])
    if y_m > 0 and x_m > 0 and y_m < step_max and x_m < step_max:  # degree grids
        lat_2d, lon_2d = np.meshgrid(y, x, indexing="ij")
        ds = ds.assign_coords(
            lat=(("y", "x"), lat_2d.astype(np.float64)),
            lon=(("y", "x"), lon_2d.astype(np.float64)),
        )
        ds["lat"].attrs = {"standard_name": "latitude", "units": "degrees_north"}
        ds["lon"].attrs = {"standard_name": "longitude", "units": "degrees_east"}
        ds["crs"] = int(0)
        ds["crs"].attrs = {
            "grid_mapping_name": "latitude_longitude",
            "longitude_of_prime_meridian": 0.0,
            "semi_major_axis": 6378137.0,
            "inverse_flattening": 298.257223563,
            "spatial_ref": 'GEOGCS["WGS 84",DATUM["WGS_1984",'
                           'SPHEROID["WGS 84",6378137,298.257223563]],'
                           'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]',
        }
        for var in ds.data_vars:
            if "y" in ds[var].dims and "x" in ds[var].dims:
                ds[var].attrs["grid_mapping"] = "crs"
                ds[var].attrs["coordinates"] = "lat lon"
    print(f"Writing: {output_path}")
    ds.to_netcdf(output_path, encoding=encoding)

    variables = ["rainfall", "air_temp_c"] + [v for v in jrc] + [v for v in wc]
    if salinity_ppt is not None:
        variables.append("salinity_ppt")

    print(
        f"\n=== SUMMARY ===\n"
        f"  rainfall: [{rainfall.min():.1f}, {rainfall.max():.1f}], "
        f"nodata replaced: {nodata_count}\n"
        f"  air_temp_c: [{air_temp_c.min():.1f}, {air_temp_c.max():.1f}]\n"
        f"  jrc_persistent: [{jrc['jrc_persistent'].min():.3f}, "
        f"{jrc['jrc_persistent'].max():.3f}]\n"
        f"  candidate habitat cells (> "
        f"{HABITAT_CANDIDATE_MIN}): {n_candidates} of {h * w}"
        f"\n  contract_version: {_ENV_NC}"
    )

    return {
        "env_path": str(output_path),
        "format": "nc",
        "aoi_slug": aoi,
        "n_days": n_days,
        "n_candidate_cells": n_candidates,
        "grid": f"{h}x{w}",
        "variables": variables,
        "contract_version": _ENV_NC,
    }


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
