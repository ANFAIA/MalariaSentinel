"""Unit tests for the M1.5 ``CoordinatorModel``.

The coordinator owns the spatial layer: ``mesa_geo.GeoSpace``,
``HabitatPatch`` agents, and the climate lookups. The per-day contract
exercised by these tests:

  * construction (build patches from a gpkg, materialise ``_cell_lookup``)
  * ``activate_patches(day)`` — set ``patch.activated`` from climate
  * ``to_dataframe()`` — return a Polars DataFrame of per-patch state
  * ``aggregate_density(mosquito_df, k_max)`` — group + join + bincount
  * ``suitability_grid()`` — 1.0 for cells with an active patch
  * ``write_state_cog(path, density, suitability, ...)`` — write 2-band COG

The tests use a synthetic AOI + a small gpkg (4 patches) so the
coordinate-lookup logic and per-patch activation can be inspected by
hand. The facade test (``test_anopheles_abm_facade.py``) exercises
the full pipeline at a larger scale.
"""
from __future__ import annotations

import json
import pathlib
from datetime import date

import geopandas as gpd
import numpy as np
import polars as pl
import pytest
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import Point

from mal_commonlib.aoi import AOI, Scale

from mal_ghana_sim.abm import (
    CoordinatorModel,
    PATCH_STATE_SCHEMA,
    PatchState,
)


# -- fixtures --------------------------------------------------------------


@pytest.fixture
def small_aoi() -> AOI:
    """A 0.1 deg x 0.1 deg AOI on the equator (10x10 at 1km resolution)."""
    return AOI.from_bbox(
        -0.05, -0.05, 0.05, 0.05,
        crs="EPSG:4326", slug="test", resolution_m=1000, scale=Scale.REGIONAL,
    )


@pytest.fixture
def four_patch_gpkg(small_aoi: AOI) -> gpd.GeoDataFrame:
    """A 4-patch gpkg at the four cells around the AOI centre."""
    h, w = small_aoi.cells_per_side()
    transform = from_bounds(*small_aoi.bbox, w, h)
    rows = [h // 2 - 1, h // 2 - 1, h // 2 + 1, h // 2 + 1]
    cols = [w // 2 - 1, w // 2 + 1, w // 2 - 1, w // 2 + 1]
    xs = transform.c + (np.array(cols) + 0.5) * transform.a
    ys = transform.f + (np.array(rows) + 0.5) * transform.e
    return gpd.GeoDataFrame(
        {
            "hab_type": ["pluvial_pool"] * 4,
            "twi_value": [10.0, 11.0, 12.0, 13.0],
            "water_frac_value": [0.5] * 4,
            "K": [1000] * 4,
            "row": rows,
            "col": cols,
            "aoi_slug": [small_aoi.slug] * 4,
        },
        geometry=[Point(float(x), float(y)) for x, y in zip(xs, ys)],
        crs=small_aoi.crs,
    )


def _synthetic_env(rain: float = 20.0, temp: float = 25.0) -> dict:
    """Build a synthetic env dict (constant-per-day)."""
    return {
        "rain_daily": lambda d, lon, lat: rain,
        "water_temp_c": lambda d, lon, lat: temp,
        "water_frac": lambda d, lon, lat: 0.5,
        "ndvi": lambda d, lon, lat: 0.5,
    }


# -- construction ----------------------------------------------------------


def test_coordinator_construction(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """The coordinator materialises the habitat patches and the cell lookup."""
    env = _synthetic_env(rain=20.0, temp=25.0)
    c = CoordinatorModel(
        small_aoi, env, four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    assert len(c.habitat_engine.patches) == 4
    assert len(c._cell_lookup) == 4
    # Patches are in the scheduler shim.
    bucket = c.schedule.agents_by_type.get(type(c.habitat_engine.patches[0]), [])
    assert len(bucket) == 4


def test_coordinator_seed_propagates_to_rng(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """The coordinator's rng is seeded with the constructor seed."""
    c1 = CoordinatorModel(
        small_aoi, _synthetic_env(), four_patch_gpkg, seed=42, start_date=date(2024, 6, 1),
    )
    c2 = CoordinatorModel(
        small_aoi, _synthetic_env(), four_patch_gpkg, seed=42, start_date=date(2024, 6, 1),
    )
    # The two coordinators should be at the same RNG state immediately
    # after construction.
    assert c1.rng.bit_generator.state == c2.rng.bit_generator.state


# -- activation -----------------------------------------------------------


def test_activate_patches_above_threshold(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """Rain above RAIN_THRESHOLD_MM activates the patch."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    assert all(p.activated for p in c.habitat_engine.patches)


def test_activate_patches_below_threshold(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """Rain below RAIN_THRESHOLD_MM deactivates the patch."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=5.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    assert not any(p.activated for p in c.habitat_engine.patches)


# -- to_dataframe ---------------------------------------------------------


def test_to_dataframe_schema(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """The patch-state DataFrame has the right schema and one row per patch."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    df = c.to_dataframe()
    assert len(df) == 4
    assert set(df.columns) == set(PATCH_STATE_SCHEMA.keys())
    for col, expected in PATCH_STATE_SCHEMA.items():
        assert df.schema[col] == expected, (
            f"column {col!r} has dtype {df.schema[col]}; expected {expected}"
        )


def test_to_dataframe_activated_column(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """The DataFrame's ``activated`` column reflects the patch state."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    df = c.to_dataframe()
    assert df["activated"].to_list() == [True] * 4


def test_to_dataframe_rain_temp_columns(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """The DataFrame's rain_d and temp_d columns match the climate env."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    df = c.to_dataframe()
    assert (df["rain_d"] == 20.0).all()
    assert (df["temp_d"] == 25.0).all()


def test_to_dataframe_cell_indices(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """The DataFrame's (row, col) matches the gpkg's (row, col)."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(), four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    df = c.to_dataframe()
    # The gpkg's row/col are 4,5,5,6 (centres around (h//2, w//2)).
    rows = sorted(df["row"].to_list())
    cols = sorted(df["col"].to_list())
    h, w = small_aoi.cells_per_side()
    expected_rows = sorted([h // 2 - 1, h // 2 - 1, h // 2 + 1, h // 2 + 1])
    expected_cols = sorted([w // 2 - 1, w // 2 + 1, w // 2 - 1, w // 2 + 1])
    assert rows == expected_rows
    assert cols == expected_cols


# -- aggregate_density ----------------------------------------------------


def test_aggregate_density_empty_mosquito_df(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """An empty mosquito DataFrame produces an all-zero density grid."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(), four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    empty = pl.DataFrame(schema={"patch_id": pl.Int64})
    grid = c.aggregate_density(empty, k_max=10)
    h, w = small_aoi.cells_per_side()
    assert grid.shape == (h, w)
    assert (grid == 0.0).all()


def test_aggregate_density_with_population(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """A non-empty mosquito DataFrame places counts at the right cell."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(), four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    h, w = small_aoi.cells_per_side()
    # 5 agents at patch 0 (cell row=h//2-1, col=w//2-1).
    rows = [h // 2 - 1] * 5
    cols = [w // 2 - 1] * 5
    df = pl.DataFrame(
        {
            "patch_id": [0] * 5,
            "row": rows,
            "col": cols,
        },
        schema={"patch_id": pl.Int64, "row": pl.Int32, "col": pl.Int32},
    )
    grid = c.aggregate_density(df, k_max=10)
    # 5 / 10 = 0.5 at (h//2-1, w//2-1); 0 elsewhere.
    assert grid[h // 2 - 1, w // 2 - 1] == 0.5
    # And nothing else is non-zero.
    total = grid.sum()
    assert total == pytest.approx(0.5, abs=1e-6)


def test_aggregate_density_clip(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """Counts > k_max are clipped to 1.0."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(), four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    h, w = small_aoi.cells_per_side()
    # 20 agents at one cell; k_max=5 → 4.0 → clipped to 1.0.
    df = pl.DataFrame(
        {
            "patch_id": [0] * 20,
            "row": [h // 2 - 1] * 20,
            "col": [w // 2 - 1] * 20,
        },
        schema={"patch_id": pl.Int64, "row": pl.Int32, "col": pl.Int32},
    )
    grid = c.aggregate_density(df, k_max=5)
    assert grid.max() == 1.0


# -- suitability ---------------------------------------------------------


def test_suitability_grid_with_active_patches(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """Active patches mark their cell as 1.0 in the suitability grid."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    grid = c.suitability_grid()
    h, w = small_aoi.cells_per_side()
    assert grid.shape == (h, w)
    # 4 cells should be 1.0.
    assert int((grid == 1.0).sum()) == 4


def test_suitability_grid_no_active_patches(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """No active patches → all-zero suitability grid."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=5.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    grid = c.suitability_grid()
    assert (grid == 0.0).all()


# -- write_state_cog ------------------------------------------------------


def test_write_state_cog_round_trip(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame, tmp_path: pathlib.Path,
) -> None:
    """The state COG is written with 2 bands, float32, EPSG:4326, tiled."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    h, w = small_aoi.cells_per_side()
    density = c.aggregate_density(
        pl.DataFrame({"patch_id": [0] * 5, "row": [h // 2 - 1] * 5, "col": [w // 2 - 1] * 5},
                     schema={"patch_id": pl.Int64, "row": pl.Int32, "col": pl.Int32}),
        k_max=10,
    )
    suitability = c.suitability_grid()
    out = tmp_path / "state.tif"
    c.write_state_cog(
        str(out), density, suitability,
        year=2024, month=6, seed=1,
    )
    assert out.exists()
    with rasterio.open(out) as src:
        assert src.count == 2
        assert src.dtypes[0] == "float32"
        assert src.crs.to_epsg() == 4326
        assert src.profile["tiled"] is True
        # Sidecar.
        sidecar = json.loads(out.with_suffix(".json").read_text())
        assert sidecar["contract_version"] == "1.0"
        assert sidecar["aoi_slug"] == "test"
        assert sidecar["year"] == 2024
        assert sidecar["month"] == 6
        assert sidecar["seed"] == 1
        assert sidecar["band_names"] == ["density", "suitability"]
        # Suitability band should have 4 cells at 1.0.
        suit_band = src.read(2)
        assert int((suit_band == 1.0).sum()) == 4
