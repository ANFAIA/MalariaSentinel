"""build_env: orchestrate the M1.3a data loaders to produce the env tensor + habitat patches.

Usage:
    uv run python -m mal_ghana_sim.scripts.build_env \\
        --aoi ghana --year 2024 --month 06 --output-dir data/runs/ghana
    uv run python -m mal_ghana_sim.scripts.build_env \\
        --aoi-slug ghana --bbox "-3.5,4.5,1.5,11.5" --crs EPSG:4326 \\
        --resolution-m 1000 --year 2024 --month 06 --output-dir data/runs/ghana

Output:
    <output-dir>/<aoi_slug>_<scale>_<YYYY>_<MM>_env.tif          (COG, 4 bands)
    <output-dir>/<aoi_slug>_<scale>_<YYYY>_<MM>_env.json         (sidecar)
    <output-dir>/<aoi_slug>_<scale>_<YYYY>_<MM>_habitat_patches.gpkg

Auth policy
-----------
CHIRPS, MERIT-DEM, and WorldCover do not require any credentials and are
always attempted. ERA5 (CDS) and MODIS (EARTHDATA_TOKEN) require auth. By
default the CLI prefers forward progress: if a loader raises on missing auth
or a transient network error, the CLI prints a clear warning to stderr and
fills the channel with the NoData sentinel (-9999.0). The --skip-era5 and
--skip-modis flags force-skip the corresponding channel even when auth is
present, which is useful for unit tests and offline dry-runs.

The output contract is documented in docs/abm-output-contract.md (v1.0).
"""
from __future__ import annotations

import json
import pathlib
from typing import Callable, Mapping

import geopandas as gpd
import numpy as np
import rasterio
import requests
import typer
import xarray as xr
from rasterio.transform import from_bounds
from shapely.geometry import Point

from mal_commonlib.aoi import AOI, Scale
from mal_commonlib.data.loaders.chirps import load_chirps_rainfall
from mal_commonlib.data.loaders.dem import load_merit_dem
from mal_commonlib.data.loaders.era5 import load_era5_temp_suitability
from mal_commonlib.data.loaders.modis import load_modis_ndvi
from mal_commonlib.data.loaders.worldcover import load_worldcover_water_frac
from mal_commonlib.terrain.twi import compute_twi


# Per docs/abm-output-contract.md §2 (env tensor): the four band names must
# appear in this order in the COG and in the band dim of the stacked array.
ENV_BAND_NAMES: tuple[str, ...] = (
    "water_frac",
    "rainfall",
    "temp_suitability",
    "ndvi",
)
NODATA_SENTINEL: float = -9999.0
GENERATOR_VERSION: str = "m1-thin-0.1.0"
CONTRACT_VERSION: str = "1.0"

# Minimal in-repo slug registry. M5+ will read this from a JSON file (or GADM).
_DEFAULT_REGISTRY: dict[str, AOI] = {
    "ghana": AOI.from_bbox(-3.5, 4.5, 1.5, 11.5, "EPSG:4326", "ghana", 1000),
}


app = typer.Typer(
    add_completion=False,
    help=(
        "Build the M1 env tensor (C_env=4, H, W) and habitat patches for an "
        "AOI + month. CHIRPS / MERIT / WorldCover work without auth. "
        "ERA5 (CDS) and MODIS (EARTHDATA_TOKEN) are auto-skipped with a "
        "warning if their credentials are missing (channel becomes NoData)."
    ),
)


# -- helpers ----------------------------------------------------------------


def _load_with_fallback(
    loader: Callable[..., xr.DataArray],
    aoi: AOI,
    year: int,
    month: int,
    channel_name: str,
    *,
    default_value: float = NODATA_SENTINEL,
) -> xr.DataArray:
    """Call a loader; on auth/network failure, return a NoData-filled channel.

    Auth/network errors are reported on stderr and the channel is filled with
    ``default_value`` (-9999.0) at the AOI's grid so the rest of the pipeline
    (stack, write) can continue. Other exceptions propagate.
    """
    h, w = aoi.cells_per_side()
    try:
        if channel_name == "elevation":
            return loader(aoi)
        return loader(aoi, year, month)
    except (RuntimeError, FileNotFoundError, OSError, requests.RequestException) as exc:
        typer.echo(
            f"WARNING: {channel_name} loader failed: {exc!r}. "
            f"Filling with NoData ({default_value}).",
            err=True,
        )
        return _empty_channel(aoi, value=default_value, band_name=channel_name)


def _empty_channel(aoi: AOI, *, value: float, band_name: str) -> xr.DataArray:
    """Return a (y, x) DataArray on the AOI's grid filled with ``value``."""
    h, w = aoi.cells_per_side()
    arr = np.full((h, w), float(value), dtype=np.float32)
    transform = from_bounds(*aoi.bbox, w, h)
    da = xr.DataArray(
        arr,
        dims=("y", "x"),
        name=band_name,
        attrs={
            "long_name": f"{band_name} (NoData fill)",
            "band_name": band_name,
            "aoi_slug": aoi.slug,
            "nodata": NODATA_SENTINEL,
            "fill": True,
        },
    )
    da.rio.write_crs(aoi.crs_obj, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    da.rio.write_nodata(NODATA_SENTINEL, inplace=True)
    return da


def _stack_env_channels(
    channels: Mapping[str, xr.DataArray],
    aoi: AOI,
) -> xr.DataArray:
    """Stack 4 named channels into a (band=4, y, x) array on the AOI's grid.

    All channels must already be on the AOI's grid (each loader is responsible
    for reprojecting to ``aoi.cells_per_side()`` and writing the AOI's CRS /
    transform). We re-assert the CRS, assign the band dimension, and emit
    a (4, H, W) float32 tensor.
    """
    missing = [name for name in ENV_BAND_NAMES if name not in channels]
    if missing:
        raise KeyError(f"channels missing from input: {missing}; got {list(channels)}")

    h, w = aoi.cells_per_side()
    transform = from_bounds(*aoi.bbox, w, h)

    arrs: list[np.ndarray] = []
    for name in ENV_BAND_NAMES:
        da = channels[name]
        if da.rio.crs is None:
            da = da.rio.write_crs(aoi.crs_obj, inplace=True)
        if da.shape != (h, w):
            raise ValueError(
                f"channel {name!r} has shape {da.shape}; expected {(h, w)} for AOI {aoi.slug}"
            )
        arrs.append(np.asarray(da.values, dtype=np.float32))

    stacked = np.stack(arrs, axis=0).astype(np.float32)
    assert stacked.shape == (4, h, w), (
        f"stacked env shape {stacked.shape} != (4, {h}, {w})"
    )

    out = xr.DataArray(
        stacked,
        dims=("band", "y", "x"),
        coords={"band": list(ENV_BAND_NAMES)},
        attrs={
            "long_name": "env tensor (4 channels)",
            "band_names": list(ENV_BAND_NAMES),
            "aoi_slug": aoi.slug,
            "nodata": NODATA_SENTINEL,
        },
    )
    out.rio.write_crs(aoi.crs_obj, inplace=True)
    out.rio.write_transform(transform, inplace=True)
    return out


def _write_env_cog(
    path: pathlib.Path,
    env: xr.DataArray,
    aoi: AOI,
    year: int,
    month: int,
) -> pathlib.Path:
    """Write the env tensor as a COG-compatible GeoTIFF + sidecar JSON.

    Conforms to docs/abm-output-contract.md §2 and §3:
    - 4 bands, dtype float32, NoData -9999.0
    - CRS = aoi.crs, transform = AOI's transform
    - band descriptions = ["water_frac", "rainfall", "temp_suitability", "ndvi"]
    - file naming = {aoi_slug}_{scale}_{year}_{month:02d}_env.tif
    - sidecar JSON next to the .tif with the same basename + .json
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    h, w = aoi.cells_per_side()
    transform = from_bounds(*aoi.bbox, w, h)
    arr = np.asarray(env.values, dtype=np.float32)
    assert arr.shape == (4, h, w), f"env shape {arr.shape} != (4, {h}, {w})"

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 4,
        "height": h,
        "width": w,
        "crs": aoi.crs,
        "transform": transform,
        "nodata": NODATA_SENTINEL,
        "tiled": True,
        "compress": "deflate",
        "blockxsize": 128,
        "blockysize": 128,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr)
        for i, name in enumerate(ENV_BAND_NAMES, start=1):
            dst.set_band_description(i, name)

    sidecar = {
        "crs": aoi.crs,
        "transform": [float(x) for x in transform[:6]],
        "aoi_slug": aoi.slug,
        "scale": aoi.scale.value,
        "year": int(year),
        "month": int(month),
        "generator_version": GENERATOR_VERSION,
        "abm_params_hash": "sha256:pending",
        "contract_version": CONTRACT_VERSION,
        "band_names": list(ENV_BAND_NAMES),
        "nodata": NODATA_SENTINEL,
        "shape": list(arr.shape),
    }
    sidecar_path = path.with_suffix(".json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2))
    return path


def _write_habitat_patches_gpkg(
    path: pathlib.Path,
    dem: xr.DataArray,
    water_frac: xr.DataArray,
    aoi: AOI,
    *,
    twi_threshold: float = 8.0,
) -> pathlib.Path:
    """Detect pluvial pool patches from TWI + water_frac, write a GeoPackage of points.

    A cell is considered a "habitat patch" if both:
      * TWI > ``twi_threshold`` (topographic accumulation)
      * water_frac > 0.0  (cell has at least some open water / wetland)

    For each candidate cell we emit a ``shapely.geometry.Point`` at the cell
    centre in EPSG:4326 (the AOI's CRS for the M1 thin slice).
    """
    twi = compute_twi(dem, cell_size_m=float(aoi.resolution_m))

    twi_arr = np.asarray(twi.values, dtype=np.float32)
    water_arr = np.asarray(water_frac.values, dtype=np.float32)
    h, w = aoi.cells_per_side()
    assert twi_arr.shape == (h, w), f"twi shape {twi_arr.shape} != {(h, w)}"
    assert water_arr.shape == (h, w), f"water_arr shape {water_arr.shape} != {(h, w)}"

    candidate_mask = (twi_arr > twi_threshold) & (water_arr > 0.0) & np.isfinite(twi_arr)
    rows, cols = np.where(candidate_mask)

    transform = from_bounds(*aoi.bbox, w, h)
    xs = transform.c + (cols + 0.5) * transform.a
    ys = transform.f + (rows + 0.5) * transform.e

    gdf = gpd.GeoDataFrame(
        {
            "twi_value": twi_arr[rows, cols].astype(np.float64),
            "water_frac_value": water_arr[rows, cols].astype(np.float64),
            "row": rows.astype(np.int32),
            "col": cols.astype(np.int32),
            "aoi_slug": aoi.slug,
        },
        geometry=[Point(float(x), float(y)) for x, y in zip(xs, ys)],
        crs=aoi.crs,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GPKG")
    return path


# -- AOI resolution ---------------------------------------------------------


def _resolve_aoi(
    aoi: str | None,
    bbox: str | None,
    crs: str,
    resolution_m: int,
    scale: Scale,
    name: str | None,
) -> AOI:
    """Build an ``AOI`` from either the slug registry or an explicit ``--bbox``."""
    if bbox is not None:
        parts = [p.strip() for p in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError(
                f"--bbox must be 4 floats 'W,S,E,N'; got {bbox!r}"
            )
        w, s, e, n = (float(x) for x in parts)
        slug = aoi if aoi else "custom"
        return AOI.from_bbox(
            west=w, south=s, east=e, north=n,
            crs=crs, slug=slug, resolution_m=resolution_m,
            name=name, scale=scale,
        )
    if aoi is None:
        raise typer.BadParameter("either --aoi or --bbox is required")
    if aoi in _DEFAULT_REGISTRY:
        return _DEFAULT_REGISTRY[aoi]
    raise typer.BadParameter(
        f"unknown AOI slug {aoi!r}; pass --bbox for a custom region, "
        f"or use one of: {sorted(_DEFAULT_REGISTRY)}"
    )


# -- Typer command ----------------------------------------------------------


@app.command()
def main(
    aoi: str | None = typer.Option(
        "ghana", "--aoi",
        help="AOI slug. Looks up the AOI in the in-repo registry (currently: ghana) "
             "or uses --bbox if both are given.",
    ),
    bbox: str | None = typer.Option(
        None, "--bbox",
        help='Optional bbox "W,S,E,N" in the CRS. If set, overrides the slug registry.',
    ),
    crs: str = typer.Option("EPSG:4326", "--crs", help="CRS for the AOI."),
    resolution_m: int = typer.Option(1000, "--resolution-m", help="AOI ground resolution in metres."),
    year: int = typer.Option(..., "--year", help="Year (e.g. 2024)."),
    month: int = typer.Option(..., "--month", min=1, max=12, help="Month (1-12)."),
    output_dir: pathlib.Path = typer.Option(..., "--output-dir", help="Directory for the env COG, sidecar, and habitat gpkg."),
    scale: Scale = typer.Option(Scale.REGIONAL, "--scale", help="Multi-scale level (regional/national/continental)."),
    name: str | None = typer.Option(None, "--name", help="Optional human-readable name for the AOI."),
    twi_threshold: float = typer.Option(
        8.0, "--twi-threshold",
        help="TWI threshold above which a cell is a pluvial pool candidate.",
    ),
    skip_era5: bool = typer.Option(
        False, "--skip-era5",
        help="Skip the ERA5 download (channel becomes NoData regardless of CDS auth).",
    ),
    skip_modis: bool = typer.Option(
        False, "--skip-modis",
        help="Skip the MODIS download (channel becomes NoData regardless of EARTHDATA_TOKEN).",
    ),
) -> None:
    """Build the M1 env tensor + habitat patches for an AOI + month."""
    if not (1 <= month <= 12):
        raise typer.BadParameter(f"month must be 1..12; got {month}")

    aoi_obj = _resolve_aoi(aoi, bbox, crs, resolution_m, scale, name)
    output_dir.mkdir(parents=True, exist_ok=True)
    h, w = aoi_obj.cells_per_side()
    suffix = f"{aoi_obj.slug}_{aoi_obj.scale.value}_{year:04d}_{month:02d}"
    env_path = output_dir / f"{suffix}_env.tif"
    habitat_path = output_dir / f"{suffix}_habitat_patches.gpkg"

    typer.echo(
        f"build_env: AOI={aoi_obj.slug} scale={aoi_obj.scale.value} "
        f"grid={h}x{w} year={year} month={month:02d}"
    )

    water_frac = _load_with_fallback(
        load_worldcover_water_frac, aoi_obj, year, month, "water_frac",
    )
    rainfall = _load_with_fallback(
        load_chirps_rainfall, aoi_obj, year, month, "rainfall",
    )

    if skip_era5:
        typer.echo("skip-era5 set: filling temp_suitability with NoData (-9999.0).", err=True)
        temp_suitability = _empty_channel(aoi_obj, value=NODATA_SENTINEL, band_name="temp_suitability")
    else:
        temp_suitability = _load_with_fallback(
            load_era5_temp_suitability, aoi_obj, year, month, "temp_suitability",
        )

    if skip_modis:
        typer.echo("skip-modis set: filling ndvi with NoData (-9999.0).", err=True)
        ndvi = _empty_channel(aoi_obj, value=NODATA_SENTINEL, band_name="ndvi")
    else:
        ndvi = _load_with_fallback(
            load_modis_ndvi, aoi_obj, year, month, "ndvi",
        )

    dem = _load_with_fallback(load_merit_dem, aoi_obj, year, month, "elevation")

    env = _stack_env_channels(
        {
            "water_frac": water_frac,
            "rainfall": rainfall,
            "temp_suitability": temp_suitability,
            "ndvi": ndvi,
        },
        aoi_obj,
    )
    _write_env_cog(env_path, env, aoi_obj, year, month)
    typer.echo(f"wrote env COG   -> {env_path}  ({(4 * h * w * 4) / (1024 ** 2):.2f} MB)")

    _write_habitat_patches_gpkg(
        habitat_path, dem, water_frac, aoi_obj, twi_threshold=twi_threshold,
    )
    typer.echo(f"wrote habitat   -> {habitat_path}")

    sidecar = env_path.with_suffix(".json")
    typer.echo(f"wrote sidecar   -> {sidecar}")


if __name__ == "__main__":
    app()
