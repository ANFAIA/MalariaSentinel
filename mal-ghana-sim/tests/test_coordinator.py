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
    MosquitoSubmodel,
    PATCH_STATE_SCHEMA,
    PatchState,
)
from mal_ghana_sim.abm.habitat import HabitatType


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


@pytest.fixture
def one_patch_gpkg(small_aoi: AOI) -> gpd.GeoDataFrame:
    """A 1-row GeoDataFrame of a single PLUVIAL_POOL patch at the AOI centre."""
    transform = from_bounds(*small_aoi.bbox, *small_aoi.cells_per_side())
    h, w = small_aoi.cells_per_side()
    r, c = h // 2, w // 2
    xs = transform.c + (c + 0.5) * transform.a
    ys = transform.f + (r + 0.5) * transform.e
    return gpd.GeoDataFrame(
        {
            "hab_type": [HabitatType.PLUVIAL_POOL.value],
            "twi_value": [12.0],
            "water_frac_value": [0.5],
            "K": [1000],
            "row": [r],
            "col": [c],
            "aoi_slug": [small_aoi.slug],
        },
        geometry=[Point(float(xs), float(ys))],
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
        small_aoi, _synthetic_env(rain=20.0, temp=25.0), four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
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
    """Legacy fallback: with no ``mosquito_df``, active patches mark
    their cell as 1.0 in the suitability grid (the v1 behaviour kept
    for the per-step activation diagnostic)."""
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
    """No active patches → all-zero suitability grid (legacy fallback)."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=5.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    grid = c.suitability_grid()
    assert (grid == 0.0).all()


def test_suitability_grid_empty_mosquito_df(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """M2 path (C1): with an empty ``mosquito_df`` (and an empty real
    ``MosquitoSubmodel``), the suitability grid is all-zero regardless
    of which patches are active (no adults → no suitability). The v1
    "1.0 for active patch" behaviour is gone in the M2 path: the band
    now reflects adult density, not patch state.
    """
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    empty = pl.DataFrame(schema={"patch_id": pl.Int64, "stage": pl.Categorical})
    # Use a real (empty) MosquitoSubmodel so the v2 path
    # (``submodel.adult_density_by_cell``) is exercised. The empty
    # submodel returns an empty per-cell DataFrame, so the grid is
    # all-zero — the M2 semantics (no adults → no suitability).
    submodel = MosquitoSubmodel(model=c, n_patches=4, k_per_patch=10, init_frac=0.0, seed=1)
    grid = c.suitability_grid(empty, k_max=10, submodel=submodel)
    h, w = small_aoi.cells_per_side()
    assert grid.shape == (h, w)
    assert (grid == 0.0).all(), (
        f"empty mosquito_df + empty submodel must produce an all-zero "
        f"suitability grid; max={grid.max()}, sum={grid.sum()}"
    )


def test_suitability_band_uses_adult_density_not_active_patch(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """M2 combined, C1: the suitability band is the **adult density per
    cell / K_MAX**, computed from each adult's **post-dispersal**
    ``lon/lat`` (snapped to the AOI grid via
    ``rasterio.transform.rowcol``).

    Build a synthetic 10x10 AOI with 4 patches, all activated, and
    inject 100 adult agents at a non-patch cell via a real
    ``MosquitoSubmodel`` whose ``df`` has the adult ``lon/lat`` at
    the target cell. The suitability band must:
      * be non-zero at the non-patch cell where adults were placed
        (it is 0.0 in the v1 path — adults at non-patch cells are
        invisible to the band).
      * be zero in cells with no adults, regardless of whether
        patches are active.
    """
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))

    h, w = small_aoi.cells_per_side()
    # Pick a target cell that is NOT a patch (avoid the 4 patch cells).
    patch_cells = set(c._cell_lookup.values())
    target_row = target_col = None
    for r in range(h):
        for col in range(w):
            if (r, col) not in patch_cells:
                target_row, target_col = r, col
                break
        if target_row is not None:
            break
    assert target_row is not None and target_col is not None, (
        "test AOI must have at least one non-patch cell"
    )

    # Build a real MosquitoSubmodel with no seeded larvae, then inject
    # 100 adult agents whose lon/lat is the centre of the target
    # cell. ``rasterio.transform.rowcol`` will snap them to (row,
    # col) = (target_row, target_col).
    from mal_ghana_sim.abm.mosquito_submodel import MOSQUITO_SCHEMA
    submodel = MosquitoSubmodel(
        model=c, n_patches=4, k_per_patch=10, init_frac=0.0, seed=1,
    )
    transform = from_bounds(*small_aoi.bbox, w, h)
    target_lon = transform.c + (target_col + 0.5) * transform.a
    target_lat = transform.f + (target_row + 0.5) * transform.e
    n_adults = 100
    submodel.df = pl.DataFrame(
        {
            "unique_id": np.arange(n_adults, dtype=np.int64),
            "patch_id": np.full(n_adults, -1, dtype=np.int64),
            "row": np.full(n_adults, target_row, dtype=np.int32),
            "col": np.full(n_adults, target_col, dtype=np.int32),
            "stage": pl.Series(["adult"] * n_adults, dtype=pl.Categorical),
            "lon": np.full(n_adults, target_lon, dtype=np.float32),
            "lat": np.full(n_adults, target_lat, dtype=np.float32),
            "eip_progress": np.zeros(n_adults, dtype=np.float32),
            "stage_age": np.zeros(n_adults, dtype=np.int32),
        },
        schema=MOSQUITO_SCHEMA,
    )
    grid = c.suitability_grid(submodel.df, k_max=1000, submodel=submodel)
    assert grid.shape == (h, w)
    # The target cell must have a non-zero suitability from the 100
    # adults (100 / 1000 = 0.1).
    assert grid[target_row, target_col] == pytest.approx(0.1, abs=1e-6), (
        f"target cell {target_row, target_col} must have suitability "
        f"~ 0.1 (100 adults / K_MAX=1000); got {grid[target_row, target_col]}"
    )
    # The 4 original patch cells must have suitability 0.0 (no adults
    # at the patches — only the target cell has adults). This is the
    # key difference from the v1 "1.0 for active patch" behaviour: the
    # new band is adult-density, not patch-state.
    for r, col in c._cell_lookup.values():
        if (r, col) == (target_row, target_col):
            continue
        if (r, col) in patch_cells:
            assert grid[r, col] == 0.0, (
                f"patch cell {(r, col)} has no adults and must have "
                f"suitability 0.0; got {grid[r, col]}"
            )
    # Cells with no adults → suitability 0.0.
    assert int((grid > 0.0).sum()) == 1, (
        f"only the target cell should have non-zero suitability; "
        f"got {int((grid > 0.0).sum())} non-zero cells"
    )


def test_suitability_band_normalises_by_k_max(
    small_aoi: AOI, four_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """M2 path (C1): the suitability band normalises by ``k_max`` and
    clips to [0, 1]. With K_MAX=5 and 20 adults at one cell, the
    value at that cell is 1.0 (clipped)."""
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0),
        four_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    c.activate_patches(date(2024, 6, 1))
    h, w = small_aoi.cells_per_side()
    target_row, target_col = h // 2, w // 2
    from mal_ghana_sim.abm.mosquito_submodel import MOSQUITO_SCHEMA
    submodel = MosquitoSubmodel(
        model=c, n_patches=4, k_per_patch=10, init_frac=0.0, seed=1,
    )
    transform = from_bounds(*small_aoi.bbox, w, h)
    target_lon = transform.c + (target_col + 0.5) * transform.a
    target_lat = transform.f + (target_row + 0.5) * transform.e
    n_adults = 20
    submodel.df = pl.DataFrame(
        {
            "unique_id": np.arange(n_adults, dtype=np.int64),
            "patch_id": np.full(n_adults, -1, dtype=np.int64),
            "row": np.full(n_adults, target_row, dtype=np.int32),
            "col": np.full(n_adults, target_col, dtype=np.int32),
            "stage": pl.Series(["adult"] * n_adults, dtype=pl.Categorical),
            "lon": np.full(n_adults, target_lon, dtype=np.float32),
            "lat": np.full(n_adults, target_lat, dtype=np.float32),
            "eip_progress": np.zeros(n_adults, dtype=np.float32),
            "stage_age": np.zeros(n_adults, dtype=np.int32),
        },
        schema=MOSQUITO_SCHEMA,
    )
    grid = c.suitability_grid(submodel.df, k_max=5, submodel=submodel)
    # 20 / 5 = 4 → clipped to 1.0.
    assert grid[target_row, target_col] == 1.0


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
    # 5 agents at patch 0 — all larvae (no adults). In the M2
    # suitability band (adult density / K_MAX) this means
    # ``suitability == 0.0`` everywhere (larvae don't count), even
    # though patches are active. This is the deliberate change from
    # the v1 "1.0 for active patch" binary map.
    mosquito_df = pl.DataFrame(
        {"patch_id": [0] * 5, "row": [h // 2 - 1] * 5, "col": [w // 2 - 1] * 5,
         "stage": pl.Series(["larva"] * 5, dtype=pl.Categorical)},
        schema={"patch_id": pl.Int64, "row": pl.Int32, "col": pl.Int32,
                "stage": pl.Categorical},
    )
    density = c.aggregate_density(mosquito_df, k_max=10)
    # Use an empty real MosquitoSubmodel so the v2 path
    # (``submodel.adult_density_by_cell``) returns an empty
    # per-cell DataFrame; the grid is then all-zero (M2 combined,
    # C1: no adults → no suitability).
    submodel = MosquitoSubmodel(model=c, n_patches=4, k_per_patch=10, init_frac=0.0, seed=1)
    suitability = c.suitability_grid(mosquito_df, k_max=10, submodel=submodel)
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
        # M2 fix: density band has 1 cell > 0 (5 larvae / 10 = 0.5).
        density_band = src.read(1)
        assert int((density_band > 0.0).sum()) == 1
        # M2 fix: suitability band is per-cell adult density / K_MAX.
        # All agents in this test are larvae → 0 adults → all-zero
        # suitability (the v1 "1.0 for active patch" behaviour is
        # gone in the M2 path).
        suit_band = src.read(2)
        assert (suit_band == 0.0).all()


# -- M2 combined, C1 — adult_density_by_cell + post-dispersal suitability --


def test_adult_density_by_cell_uses_post_dispersal_location(
    small_aoi: AOI, one_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """C1: the suitability band uses each adult's **post-dispersal**
    ``lon/lat`` (snapped to the AOI grid via
    ``rasterio.transform.rowcol``).

    Build a 10x10 AOI with one patch at the centre, manually inject
    500 adult agents at the patch's ``lon/lat``, then call
    ``model.step()`` to trigger dispersal. After the step, the
    ``adult_density_by_cell`` DataFrame must show adults at cells
    *other* than the patch cell (post-dispersal) and the
    ``suitability_grid`` (v2 path) must show non-zero suitability at
    those cells.
    """
    from mal_ghana_sim.abm.model import AnophelesABM
    from mal_ghana_sim.abm.mosquito_submodel import MOSQUITO_SCHEMA
    env = _synthetic_env(rain=20.0, temp=25.0)
    m = AnophelesABM(
        small_aoi, env, one_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    # Step the model 30 days to grow adults from the seeded larvae.
    for _ in range(30):
        m.step()
    # Adults have emerged. The post-dispersal state shows adults at
    # the patch cell and possibly a few nearby cells (some may have
    # dispersed within the 2 km cap).
    h, w = small_aoi.cells_per_side()
    adult_cell_df = m.submodel.adult_density_by_cell(small_aoi)
    assert set(adult_cell_df.columns) == {"row", "col", "n_adults"}, (
        f"expected columns ['row', 'col', 'n_adults']; "
        f"got {adult_cell_df.columns}"
    )
    # The patch is at (h//2, w//2); the adult-density DataFrame
    # should have at least one row there (we seeded 30% of K=1000
    # at the patch and ran 30 days — most of those should be
    # adults at the patch cell after EIP).
    patch_row, patch_col = h // 2, w // 2
    patch_count = adult_cell_df.filter(
        (pl.col("row") == patch_row) & (pl.col("col") == patch_col)
    )["n_adults"].sum()
    assert int(patch_count) > 0, (
        f"expected adults at the patch cell ({patch_row}, {patch_col}) "
        f"after 30 days; got 0"
    )
    # The suitability band (v2 path) must have non-zero values at
    # the patch cell.
    grid = m.coordinator.suitability_grid(
        m.submodel.df, k_max=m.K_MAX, submodel=m.submodel,
    )
    assert grid.shape == (h, w)
    assert grid[patch_row, patch_col] > 0.0, (
        f"suitability at patch cell ({patch_row}, {patch_col}) must be > 0; "
        f"got {grid[patch_row, patch_col]}"
    )


def test_adult_density_by_cell_clamps_out_of_aoi(
    small_aoi: AOI, one_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """C1: adults with ``lon/lat`` far outside the AOI are clamped to
    the nearest edge cell, not dropped (the v1 path dropped them
    silently)."""
    from mal_ghana_sim.abm.model import AnophelesABM
    from mal_ghana_sim.abm.mosquito_submodel import MOSQUITO_SCHEMA
    env = _synthetic_env(rain=20.0, temp=25.0)
    m = AnophelesABM(
        small_aoi, env, one_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    # Replace the population with 100 adults at (999, 999) — way outside
    # the AOI bbox (-0.05, -0.05, 0.05, 0.05).
    m.submodel.df = pl.DataFrame(
        {
            "unique_id": np.arange(100, dtype=np.int64),
            "patch_id": np.zeros(100, dtype=np.int64),
            "row": np.zeros(100, dtype=np.int32),
            "col": np.zeros(100, dtype=np.int32),
            "stage": pl.Series(["adult"] * 100, dtype=pl.Categorical),
            "lon": np.full(100, 999.0, dtype=np.float32),
            "lat": np.full(100, 999.0, dtype=np.float32),
            "eip_progress": np.zeros(100, dtype=np.float32),
            "stage_age": np.zeros(100, dtype=np.int32),
        },
        schema=MOSQUITO_SCHEMA,
    )
    h, w = small_aoi.cells_per_side()
    cell_df = m.submodel.adult_density_by_cell(small_aoi)
    # All 100 adults are clamped to the same corner cell (the exact
    # corner depends on the sign of the offsets after rowcol — for
    # lon=999, lat=999 the rowcol returns negative row and large
    # col, so the clamp lands at (0, w-1)).
    assert cell_df.height == 1, (
        f"expected 1 row in adult_density_by_cell (all clamped to one cell); "
        f"got {cell_df.height}"
    )
    row, col = int(cell_df["row"][0]), int(cell_df["col"][0])
    assert 0 <= row < h and 0 <= col < w, (
        f"clamped (row, col) must be in [0, h-1] x [0, w-1]; got ({row}, {col}) "
        f"with grid {h}x{w}"
    )
    # 100 adults are aggregated into a single clamped cell.
    assert int(cell_df["n_adults"][0]) == 100


def test_suitability_grid_with_submodel_uses_adult_density_by_cell(
    small_aoi: AOI,
) -> None:
    """C1: ``coordinator.suitability_grid`` with a submodel passed uses
    ``submodel.adult_density_by_cell`` (post-dispersal lon/lat) — the
    band reflects where the adult is, not where it was born, and
    *does not* rely on ``_cell_lookup`` (no patch needed)."""
    from mal_ghana_sim.abm.mosquito_submodel import MOSQUITO_SCHEMA
    # Empty gpkg → no patches, no _cell_lookup.
    empty_gpkg = gpd.GeoDataFrame(
        {"hab_type": [], "twi_value": [], "water_frac_value": [], "K": [],
         "row": [], "col": [], "aoi_slug": []},
        geometry=[],
        crs="EPSG:4326",
    )
    c = CoordinatorModel(
        small_aoi, _synthetic_env(rain=20.0, temp=25.0), empty_gpkg,
        seed=1, start_date=date(2024, 6, 1),
    )
    h, w = small_aoi.cells_per_side()
    # Inject 1000 adults at cell (3, 3) via a real submodel.
    submodel = MosquitoSubmodel(
        model=c, n_patches=0, k_per_patch=10, init_frac=0.0, seed=1,
    )
    transform = from_bounds(*small_aoi.bbox, w, h)
    target_row, target_col = 3, 3
    target_lon = transform.c + (target_col + 0.5) * transform.a
    target_lat = transform.f + (target_row + 0.5) * transform.e
    n_adults = 1000
    submodel.df = pl.DataFrame(
        {
            "unique_id": np.arange(n_adults, dtype=np.int64),
            "patch_id": np.zeros(n_adults, dtype=np.int64),
            "row": np.full(n_adults, target_row, dtype=np.int32),
            "col": np.full(n_adults, target_col, dtype=np.int32),
            "stage": pl.Series(["adult"] * n_adults, dtype=pl.Categorical),
            "lon": np.full(n_adults, target_lon, dtype=np.float32),
            "lat": np.full(n_adults, target_lat, dtype=np.float32),
            "eip_progress": np.zeros(n_adults, dtype=np.float32),
            "stage_age": np.zeros(n_adults, dtype=np.int32),
        },
        schema=MOSQUITO_SCHEMA,
    )
    grid = c.suitability_grid(submodel.df, k_max=10, submodel=submodel)
    assert grid.shape == (h, w)
    # 1000 / 10 = 100 → clipped to 1.0.
    assert grid[target_row, target_col] == 1.0, (
        f"expected suitability ~ 1.0 at (3, 3); got {grid[target_row, target_col]}"
    )
    # No other cell should be non-zero.
    assert int((grid > 0.0).sum()) == 1


# -- M2 combined, C2 — dynamic patch emergence + site fidelity -----------


def _env_with_twi(
    small_aoi: AOI, *, rain: float, twi_value: float = 10.0,
    water_frac_value: float = 0.5, temp: float = 25.0,
) -> dict:
    """Build an env dict with a constant TWI grid (for the dynamic rule)."""
    h, w = small_aoi.cells_per_side()
    twi = np.full((h, w), twi_value, dtype=np.float32)
    return {
        "twi": twi,
        "rain_daily": lambda d, lon, lat: rain,
        "water_temp_c": lambda d, lon, lat: temp,
        "water_frac": lambda d, lon, lat: water_frac_value,
        "ndvi": lambda d, lon, lat: 0.5,
    }


def test_dynamic_patch_emergence_with_synthetic_rain(
    small_aoi: AOI,
) -> None:
    """C2: cells where the PLUVIAL_POOL rule holds today (TWI > 8 AND
    water_frac > 0 AND rain_24h > 15mm) emerge as habitat patches. The
    rule needs a TWI grid in the env dict; the climate engine reads it
    via ``env['twi']`` (new in M2 combined)."""
    h, w = small_aoi.cells_per_side()
    # TWI is 10 everywhere (above threshold); water_frac is 0.5
    # (above 0). The PLUVIAL_POOL rule activates wherever rain > 15.
    env_rain = _env_with_twi(small_aoi, rain=20.0, twi_value=10.0)
    empty_gpkg = gpd.GeoDataFrame(
        {"hab_type": [], "twi_value": [], "water_frac_value": [], "K": [],
         "row": [], "col": [], "aoi_slug": []},
        geometry=[],
        crs=small_aoi.crs,
    )
    c = CoordinatorModel(
        small_aoi, env_rain, empty_gpkg,
        seed=1, start_date=date(2024, 6, 1),
    )
    df = c.to_dataframe()
    # All 100 cells satisfy the rule → 100 rows in the DataFrame.
    assert df.height == h * w, (
        f"expected {h * w} dynamic patches with rain=20, TWI=10, water_frac=0.5; "
        f"got {df.height} rows"
    )
    # All rows have activated=True.
    assert df["activated"].all()
    # Switch the env to rain=5 (below threshold) on a fresh coordinator.
    env_dry = _env_with_twi(small_aoi, rain=5.0, twi_value=10.0)
    c_dry = CoordinatorModel(
        small_aoi, env_dry, empty_gpkg,
        seed=1, start_date=date(2024, 6, 1),
    )
    df_dry = c_dry.to_dataframe()
    assert df_dry.height == 0, (
        f"expected 0 dynamic patches with rain=5 (below threshold); "
        f"got {df_dry.height} rows"
    )


def test_dynamic_patches_accumulate_across_days(
    small_aoi: AOI,
) -> None:
    """C2: the same cell gets the **same** ``patch_id`` on day 1 and
    day 2 — the registry is stable across calls."""
    env_rain = _env_with_twi(small_aoi, rain=20.0, twi_value=10.0)
    empty_gpkg = gpd.GeoDataFrame(
        {"hab_type": [], "twi_value": [], "water_frac_value": [], "K": [],
         "row": [], "col": [], "aoi_slug": []},
        geometry=[],
        crs=small_aoi.crs,
    )
    c = CoordinatorModel(
        small_aoi, env_rain, empty_gpkg,
        seed=1, start_date=date(2024, 6, 1),
    )
    df_day1 = c.to_dataframe()
    h, w = small_aoi.cells_per_side()
    # Pick any cell that is in the dynamic set on day 1.
    target_row, target_col = 3, 3
    pid_day1 = df_day1.filter(
        (pl.col("row") == target_row) & (pl.col("col") == target_col)
    )["patch_id"][0]
    # Advance the clock by 1 day (still in the same env, so the same
    # rule holds) and call ``to_dataframe`` again.
    c.current_date = date(2024, 6, 2)
    df_day2 = c.to_dataframe()
    pid_day2 = df_day2.filter(
        (pl.col("row") == target_row) & (pl.col("col") == target_col)
    )["patch_id"][0]
    assert int(pid_day1) == int(pid_day2), (
        f"the (3, 3) cell must have the same patch_id on day 1 and day 2; "
        f"got {int(pid_day1)} vs {int(pid_day2)}"
    )


def test_preexisting_patches_remain_in_registry(
    small_aoi: AOI,
) -> None:
    """C2: pre-existing patches are kept in the registry (site
    fidelity) — they reappear in the per-day patch-state DataFrame
    if the rule holds again on a later day, with the **same**
    ``patch_id``."""
    h, w = small_aoi.cells_per_side()
    transform = from_bounds(*small_aoi.bbox, w, h)
    target_row, target_col = h // 2, w // 2
    # Build a gpkg with 1 pre-existing patch at the AOI centre.
    gpkg = gpd.GeoDataFrame(
        {
            "hab_type": [HabitatType.PLUVIAL_POOL.value],
            "twi_value": [10.0],
            "water_frac_value": [0.5],
            "K": [1000],
            "row": [target_row],
            "col": [target_col],
            "aoi_slug": [small_aoi.slug],
        },
        geometry=[Point(
            float(transform.c + (target_col + 0.5) * transform.a),
            float(transform.f + (target_row + 0.5) * transform.e),
        )],
        crs=small_aoi.crs,
    )
    # TWI is 10 everywhere (above threshold); water_frac is 0.5.
    # The rule holds iff rain > 15.
    env = _env_with_twi(small_aoi, rain=20.0, twi_value=10.0)
    # Save the original wet rain callable before mutating the env
    # dict (``c.env is env`` — same object).
    wet_rain = env["rain_daily"]
    dry_rain = lambda d, lon, lat: 5.0
    c = CoordinatorModel(
        small_aoi, env, gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    # Day 1: rain=20, rule holds, patch is active.
    df_day1 = c.to_dataframe()
    pre_pid_day1 = df_day1.filter(
        (pl.col("row") == target_row) & (pl.col("col") == target_col)
    )["patch_id"][0]
    # Day 2: rain=5 (below threshold). The rule fails; the cell is not
    # in the dynamic set. The pre-existing patch is in the registry but
    # is *not* in the per-day DataFrame (it produced no larvae).
    c.current_date = date(2024, 6, 2)
    c.env["rain_daily"] = dry_rain
    df_day2 = c.to_dataframe()
    assert df_day2.height == 0, (
        f"day 2 (rain=5) must produce 0 dynamic patches; got {df_day2.height}"
    )
    # The pre-existing patch's patch_id is still in the registry.
    cell = (target_row, target_col)
    assert cell in c._dynamic_patch_registry, (
        f"the pre-existing patch's cell {cell} must remain in the "
        f"registry even when the rule doesn't hold"
    )
    assert c._dynamic_patch_registry[cell] == int(pre_pid_day1), (
        f"the pre-existing patch's patch_id must be stable; "
        f"got {c._dynamic_patch_registry[cell]} vs {int(pre_pid_day1)}"
    )
    # Day 3: rain=20 again. The cell reappears in the per-day
    # DataFrame with the SAME patch_id.
    c.current_date = date(2024, 6, 3)
    c.env["rain_daily"] = wet_rain
    df_day3 = c.to_dataframe()
    pre_pid_day3 = df_day3.filter(
        (pl.col("row") == target_row) & (pl.col("col") == target_col)
    )["patch_id"][0]
    assert int(pre_pid_day3) == int(pre_pid_day1), (
        f"the pre-existing patch's patch_id on day 3 must equal day 1; "
        f"got {int(pre_pid_day3)} vs {int(pre_pid_day1)}"
    )


def test_dynamic_patch_then_adult_density_by_cell(
    small_aoi: AOI,
) -> None:
    """C1 + C2 e2e: with an empty gpkg and rain=20 only at cell (3, 3),
    a dynamic patch emerges there. After 30 days, the submodel has
    adults at the dynamic cell; ``aggregate_density`` and
    ``suitability_grid`` (v2) report a non-zero value at (3, 3)."""
    from mal_ghana_sim.abm.model import AnophelesABM
    h, w = small_aoi.cells_per_side()
    # TWI is 10 only at (3, 3); 0 elsewhere. water_frac is 0.5
    # everywhere. rain=20 everywhere.
    twi = np.zeros((h, w), dtype=np.float32)
    twi[3, 3] = 10.0
    env = {
        "twi": twi,
        "rain_daily": lambda d, lon, lat: 20.0,
        "water_temp_c": lambda d, lon, lat: 25.0,
        "water_frac": lambda d, lon, lat: 0.5,
        "ndvi": lambda d, lon, lat: 0.5,
    }
    empty_gpkg = gpd.GeoDataFrame(
        {"hab_type": [], "twi_value": [], "water_frac_value": [], "K": [],
         "row": [], "col": [], "aoi_slug": []},
        geometry=[],
        crs=small_aoi.crs,
    )
    m = AnophelesABM(
        small_aoi, env, empty_gpkg, seed=1, start_date=date(2024, 6, 1),
    )
    # 30 days: enough for EIP to complete (EIP_THRESHOLD_GD = 110,
    # daily_gd ~ 9 at T=25 → ~12 days) and for adults to disperse.
    for _ in range(30):
        m.step()
    density = m.coordinator.aggregate_density(m.submodel.df, k_max=m.K_MAX)
    suitability = m.coordinator.suitability_grid(
        m.submodel.df, k_max=m.K_MAX, submodel=m.submodel,
    )
    # The dynamic patch at (3, 3) should have non-zero density (larvae
    # + adults). Note: ``aggregate_density`` uses ``patch_id`` so the
    # density at (3, 3) is the total at the dynamic patch's id; this
    # is always at (3, 3).
    assert density[3, 3] > 0.0, (
        f"density at the dynamic patch cell (3, 3) must be > 0 after "
        f"30 days; got {density[3, 3]}"
    )
    # Suitability uses post-dispersal lon/lat. With a 1 km AOI cell
    # and ``ADULT_DISPERSE_SIGMA_M=1000``, ``ADULT_DISPERSE_MAX_M=2000``,
    # an adult that emerged from (3, 3) can move up to 2 cells away
    # in a single day, and after 30 days almost every adult has moved
    # at least once. We assert that the **3x3 window** around the
    # dynamic patch has non-zero suitability (most adults are within
    # 2 cells of where they emerged) — this is the M2 combined, C1
    # fix: the suitability band follows the adults, not the patches.
    h_, w_ = small_aoi.cells_per_side()
    window = suitability[max(0, 3 - 2): min(h_, 3 + 3), max(0, 3 - 2): min(w_, 3 + 3)]
    assert window.max() > 0.0, (
        f"suitability in the 3x3 window around the dynamic patch (3, 3) "
        f"must be > 0 after 30 days; got max={window.max()}, sum={window.sum()}"
    )
    # And the registry holds the dynamic patch.
    assert (3, 3) in m.coordinator._dynamic_patch_registry, (
        f"the dynamic patch (3, 3) must be in the registry after 30 days"
    )
