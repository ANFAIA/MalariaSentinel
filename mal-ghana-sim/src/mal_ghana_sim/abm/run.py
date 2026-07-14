"""``abm_run`` CLI entry point for the M1 ABM thin slice.

Run the Mesa-Geo ABM for an AOI + month and write the state COG per
``docs/abm-output-contract.md`` §1. The CLI is offline-friendly: the
env and habitat inputs are *files* (not network calls), so a test can
exercise the full pipeline with synthetic GeoTIFFs and a 1-row gpkg.

Usage:
    uv run python -m mal_ghana_sim.abm.run \\
        --aoi ghana --year 2024 --month 6 \\
        --env data/runs/ghana/ghana_regional_2024_06_env.tif \\
        --habitat data/runs/ghana/ghana_regional_2024_06_habitat_patches.gpkg \\
        --output data/runs/ghana/ghana_regional_2024_06_seed0001.tif \\
        --seed 1 --days 30
"""
from __future__ import annotations

import json
import math
import pathlib
from datetime import date, timedelta

import geopandas as gpd
import numpy as np
import rasterio
import typer
import xarray as xr

from mal_commonlib.aoi import AOI, Scale

from .model import AnophelesABM

app = typer.Typer(
    add_completion=False,
    help=(
        "Run the M1 thin-slice ABM (Mesa-Geo v0.9.3, 2 stages, PLUVIAL_POOL) "
        "for an AOI + month. Writes the state COG per docs/abm-output-contract.md."
    ),
)

# Minimal in-repo slug registry (mirrors scripts/build_env.py).
_DEFAULT_REGISTRY: dict[str, AOI] = {
    "ghana": AOI.from_bbox(-3.5, 4.5, 1.5, 11.5, "EPSG:4326", "ghana", 1000),
}


def _resolve_aoi(
    aoi: str | None,
    bbox: str | None,
    crs: str,
    resolution_m: int,
    scale: Scale,
) -> AOI:
    if bbox is not None:
        parts = [p.strip() for p in bbox.split(",")]
        if len(parts) != 4:
            raise typer.BadParameter("--bbox must be 4 floats 'W,S,E,N'")
        w, s, e, n = (float(x) for x in parts)
        slug = aoi if aoi else "custom"
        return AOI.from_bbox(
            west=w, south=s, east=e, north=n,
            crs=crs, slug=slug, resolution_m=resolution_m, scale=scale,
        )
    if aoi is None:
        raise typer.BadParameter("either --aoi or --bbox is required")
    if aoi in _DEFAULT_REGISTRY:
        return _DEFAULT_REGISTRY[aoi]
    raise typer.BadParameter(
        f"unknown AOI slug {aoi!r}; pass --bbox for a custom region, "
        f"or use one of: {sorted(_DEFAULT_REGISTRY)}"
    )


def _suit_to_c(s: float) -> float:
    """Invert the Mordecai parabolic suitability back to deg C.

    The env COG stores ``temp_suitability`` in [0, 1] (Mordecai et al.
    2013: ``s = clip(1 - ((T - 25) / 8) ** 2, 0, 1)``, peak at 25 deg C,
    zero outside 17-33 deg C). The ABM code (mosquito_submodel.
    _larva_growth) treats ``water_temp_c`` as **deg C** and computes
    daily GD as ``max(0, T - 16)``, so passing the raw [0, 1] value
    makes that formula always 0 and the EIP never accumulates.

    We invert the *lower* branch (``T <= 25``), which is the
    biologically relevant range for Anopheles gambiae s.s. (the species
    goes dormant below ~17 deg C). Maps:

        s = 1.00 -> 25.00 deg C (peak)
        s = 0.75 -> 21.00 deg C
        s = 0.50 -> 19.34 deg C
        s = 0.00 -> 17.00 deg C
    """
    s = max(0.0, min(1.0, float(s)))
    return 25.0 - 8.0 * math.sqrt(1.0 - s)


def _load_env_dict(env_path: pathlib.Path) -> dict:
    """Read the env COG and pack it into the dict shape ClimateEngine expects.

    For the thin slice we read the 4 bands as numpy arrays and return
    callable shims (constant per day) — daily CHIRPS interpolation is
    M7+. The shim reads from in-memory arrays to avoid round-trips.

    Temperature mapping
    -------------------
    The ``temp_suitability`` band (Mordecai parabolic, [0, 1]) is
    inverted to deg C via :func:`_suit_to_c` before being returned as
    ``water_temp_c`` (the ABM EIP code expects deg C, not the raw
    normalised suitability).
    """
    with rasterio.open(env_path) as src:
        bands = src.read().astype(np.float32)
        names = src.descriptions
    by_name: dict[str, np.ndarray] = {
        (names[i] if names[i] else f"band{i}"): bands[i] for i in range(bands.shape[0])
    }
    transform = rasterio.transform.Affine(*src.transform[:6])
    h, w = bands.shape[1], bands.shape[2]

    def _value(name: str):
        arr = by_name.get(name)
        if arr is None:
            return lambda date, lon, lat: 0.0
        if name == "temp_suitability":
            # The suitability band is normalised [0, 1] — convert back
            # to deg C (lower branch of the Mordecai parabolic) so the
            # ABM's EIP formula max(0, T - 16) produces positive values.
            def _lookup(date, lon, lat):
                from rasterio.transform import rowcol
                r, c = rowcol(transform, float(lon), float(lat))
                r = int(r); c = int(c)
                if not (0 <= r < h and 0 <= c < w):
                    return 25.0  # safe default (peak)
                return _suit_to_c(arr[r, c])
            return _lookup
        # Constant-per-cell lookup keyed by lon/lat.
        def _lookup(date, lon, lat):
            from rasterio.transform import rowcol
            r, c = rowcol(transform, float(lon), float(lat))
            r = int(r); c = int(c)
            if not (0 <= r < h and 0 <= c < w):
                return 0.0
            return float(arr[r, c])
        return _lookup

    return {
        "rain_daily": _value("rainfall"),
        # Suitability [0, 1] is converted to deg C inside _value() so
        # the ABM EIP code (max(0, T - 16)) sees a real temperature.
        "water_temp_c": _value("temp_suitability"),
        "water_frac": _value("water_frac"),
        "ndvi": _value("ndvi"),
    }


@app.command()
def main(
    aoi: str | None = typer.Option("ghana", "--aoi", help="AOI slug."),
    bbox: str | None = typer.Option(None, "--bbox", help='Optional bbox "W,S,E,N".'),
    crs: str = typer.Option("EPSG:4326", "--crs", help="CRS for the AOI."),
    resolution_m: int = typer.Option(1000, "--resolution-m", help="Ground resolution (m)."),
    scale: Scale = typer.Option(Scale.REGIONAL, "--scale"),
    year: int = typer.Option(..., "--year"),
    month: int = typer.Option(..., "--month", min=1, max=12),
    seed: int = typer.Option(1, "--seed"),
    env: pathlib.Path = typer.Option(..., "--env", help="Path to the env COG (build_env output)."),
    habitat: pathlib.Path = typer.Option(..., "--habitat", help="Path to the habitat patches gpkg."),
    output: pathlib.Path = typer.Option(..., "--output", help="Path to write the state COG."),
    days: int = typer.Option(30, "--days", min=1, max=366),
) -> None:
    """Run the M1 ABM and write the state COG for (AOI, year, month, seed)."""
    if not (1 <= month <= 12):
        raise typer.BadParameter(f"month must be 1..12; got {month}")

    aoi_obj = _resolve_aoi(aoi, bbox, crs, resolution_m, scale)
    if not env.exists():
        raise typer.BadParameter(f"--env not found: {env}")
    if not habitat.exists():
        raise typer.BadParameter(f"--habitat not found: {habitat}")

    env_dict = _load_env_dict(env)
    gdf = gpd.read_file(str(habitat))

    start = date(int(year), int(month), 1)
    model = AnophelesABM(
        aoi_obj, env_dict, gdf, seed=int(seed), start_date=start,
    )
    for _ in range(int(days)):
        model.step()

    output.parent.mkdir(parents=True, exist_ok=True)
    model.snapshot(str(output), year=int(year), month=int(month), seed=int(seed))
    typer.echo(
        f"abm_run: AOI={aoi_obj.slug} year={year} month={month:02d} "
        f"seed={seed} days={days} -> {output}"
    )


if __name__ == "__main__":
    app()
