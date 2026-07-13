"""Smoke tests for the M1.5 Mesa-Geo + Polars ABM thin slice.

All tests run offline — the env inputs are synthetic dicts / small
GeoTIFFs, not the real data loaders. The e2e test builds a 10x10
synthetic env + 1-row habitat gpkg and runs 30 days of simulation.

M1.5 changes from M1.4:
  * ``MosquitoAgent`` (Mesa-Geo) is gone. The mosquito population is a
    ``polars.DataFrame`` on ``AnophelesABM.submodel.df``.
  * ``AnophelesABM.schedule`` still exists (delegated to the
    coordinator's Mesa-Geo scheduler shim) so the HabitatPatch
    ``step()`` contract is honoured.
"""
from __future__ import annotations

import json
import pathlib
import time
from datetime import date

import geopandas as gpd
import numpy as np
import pytest
import rasterio
import typer.testing
from rasterio.transform import from_bounds
from shapely.geometry import Point

from mal_commonlib.aoi import AOI, Scale

from mal_ghana_sim.abm import (
    AnophelesABM,
    CoordinatorModel,
    MosquitoSubmodel,
    PatchState,
    climate,
    habitat,
    habitat_engine,
    model,
    scheduler,
)
from mal_ghana_sim.abm.eip import (
    EIP_BASE_TEMP_C,
    EIP_THRESHOLD_GD,
    accumulate_eip,
    is_infective,
)
from mal_ghana_sim.abm.habitat import HabitatPatch, HabitatType
from mal_ghana_sim.abm.habitat_engine import HabitatEngine
from mal_ghana_sim.abm.run import app as run_app
from mal_ghana_sim.abm.scheduler import RandomActivationByTypeShim


runner = typer.testing.CliRunner()


# -- fixtures ---------------------------------------------------------------


@pytest.fixture
def small_aoi() -> AOI:
    """A 0.1 deg x 0.1 deg AOI on the equator (10x10 at 1km resolution)."""
    return AOI.from_bbox(
        -0.05, -0.05, 0.05, 0.05,
        crs="EPSG:4326", slug="test", resolution_m=1000, scale=Scale.REGIONAL,
    )


@pytest.fixture
def one_patch_gpkg(small_aoi: AOI) -> gpd.GeoDataFrame:
    """A 1-row GeoDataFrame of a single PLUVIAL_POOL patch at the AOI centre."""
    transform = from_bounds(*small_aoi.bbox, *small_aoi.cells_per_side())
    h, w = small_aoi.cells_per_side()
    # Centre cell of the grid.
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


def _synthetic_env(
    small_aoi: AOI, *, rain: float = 20.0, temp: float = 25.0,
) -> dict:
    """Build a synthetic env dict with constant rain/temp suitable for activation."""
    h, w = small_aoi.cells_per_side()
    return {
        "rain_daily": lambda d, lon, lat: rain,
        "water_temp_c": lambda d, lon, lat: temp,
        "water_frac": lambda d, lon, lat: 0.5,
        "ndvi": lambda d, lon, lat: 0.5,
    }


# -- eip tests --------------------------------------------------------------


def test_eip_accumulation() -> None:
    """EIP accumulation is max(0, T - 16) and the threshold is 110 GD."""
    assert accumulate_eip(0.0, 25.0) == 9.0
    # 100 prior + (30 - 16) = 114. The brief suggested 130, but
    # daily_gd = max(0, T - T_base) gives 14, not 30. The contract is
    # the design doc; the test asserts the function's actual math.
    assert accumulate_eip(100.0, 30.0) == 114.0
    assert is_infective(110.0) is True
    assert is_infective(109.9) is False
    # Below base temperature contributes 0.
    assert accumulate_eip(50.0, 10.0) == 50.0
    # At base temperature contributes 0.
    assert accumulate_eip(200.0, EIP_BASE_TEMP_C) == 200.0


# -- mosquito population construction (M1.5: Polars DataFrame) ------------


def test_mosquito_population_construction(small_aoi: AOI, one_patch_gpkg: gpd.GeoDataFrame) -> None:
    """The M1.5 AnophelesABM seeds the mosquito population as a Polars DataFrame.

    The M1.4 ``MosquitoAgent`` (per-agent Python object) is gone; the
    population now lives in ``AnophelesABM.submodel.df``. The
    ``K_MAX * init_frac`` seeding rule is unchanged.
    """
    env = _synthetic_env(small_aoi)
    m = AnophelesABM(small_aoi, env, one_patch_gpkg, seed=1, start_date=date(2024, 6, 1))
    df = m.submodel.df
    expected_n = int(round(m.K_MAX * 0.3))  # init_frac=0.3, 1 patch
    assert len(df) == expected_n, (
        f"submodel must seed K_MAX*init_frac larvae; "
        f"got {len(df)}, expected {expected_n}"
    )
    assert df["stage"].to_list() == ["larva"] * expected_n
    # Patch_id is the index of the only patch (0).
    assert df["patch_id"].to_list() == [0] * expected_n
    # eip_progress and stage_age are zero on the seeded frame.
    assert df["eip_progress"].sum() == 0.0
    assert df["stage_age"].sum() == 0


# -- habitat activation + mortality ----------------------------------------


def test_habitat_patch_rain_activation(small_aoi: AOI, one_patch_gpkg: gpd.GeoDataFrame) -> None:
    """PLUVIAL_POOL activates iff rain_24h > 15 mm."""
    env = _synthetic_env(small_aoi)
    m = AnophelesABM(small_aoi, env, one_patch_gpkg, seed=1, start_date=date(2024, 6, 1))
    patch = m.habitat_engine.patches[0]
    patch.activate(20.0, 25.0)
    assert patch.activated is True
    patch.activate(5.0, 25.0)
    assert patch.activated is False


def test_habitat_mortality_density_dependent(small_aoi: AOI, one_patch_gpkg: gpd.GeoDataFrame) -> None:
    """mortality with density_dep=True returns > 0 for N > K; False returns 0."""
    env = _synthetic_env(small_aoi)
    m = AnophelesABM(small_aoi, env, one_patch_gpkg, seed=1, start_date=date(2024, 6, 1))
    patch = m.habitat_engine.patches[0]
    assert patch.mortality(200, density_dep=True) > 0
    assert patch.mortality(200, density_dep=False) == 0
    # No deaths if N <= K (survival ~ 0.95).
    assert patch.mortality(50, density_dep=True) >= 0


# -- scheduler shim --------------------------------------------------------


def test_random_activation_by_type_steps() -> None:
    """scheduler.step() runs the .step() of every agent in every type bucket."""
    # Build a stub model with .rng (numpy Generator).
    class _StubModel:
        def __init__(self):
            import numpy as np
            self.rng = np.random.default_rng(0)

    stub = _StubModel()
    sched = RandomActivationByTypeShim(stub)

    calls: list[tuple[str, int]] = []

    class _Patch:
        def step(self) -> None:
            calls.append(("patch", id(self)))

    class _Larva:
        def step(self) -> None:
            calls.append(("larva", id(self)))

    class _Adult:
        def step(self) -> None:
            calls.append(("adult", id(self)))

    p = _Patch(); l = _Larva(); a = _Adult()
    sched.add(p, type_key=_Patch)
    sched.add(l, type_key=_Larva)
    sched.add(a, type_key=_Adult)
    sched.step()

    types_run = sorted(name for name, _ in calls)
    assert types_run == ["adult", "larva", "patch"], f"missing types: {types_run}"
    # counts() works.
    counts = sched.counts()
    assert counts == {_Patch: 1, _Larva: 1, _Adult: 1}


# -- end-to-end rollout ----------------------------------------------------


def test_e2e_rollout_synthetic(
    small_aoi: AOI,
    one_patch_gpkg: gpd.GeoDataFrame,
    tmp_path: pathlib.Path,
) -> None:
    """Run 30 days on a 10x10 synthetic env with 1 patch, write the state COG."""
    env = _synthetic_env(small_aoi, rain=20.0, temp=25.0)
    m = AnophelesABM(
        small_aoi, env, one_patch_gpkg, seed=1, start_date=date(2024, 6, 1),
    )

    t0 = time.perf_counter()
    for _ in range(30):
        m.step()
    elapsed = time.perf_counter() - t0
    assert elapsed < 30.0, f"30-day rollout took {elapsed:.2f}s; expected < 30s"

    output = tmp_path / "state.tif"
    m.snapshot(str(output), year=2024, month=6, seed=1)
    assert output.exists(), f"state COG missing: {output}"

    with rasterio.open(output) as src:
        assert src.count == 2, f"state COG must have 2 bands; got {src.count}"
        assert src.dtypes[0] == "float32", f"dtype must be float32; got {src.dtypes[0]}"
        assert src.crs.to_epsg() == 4326, f"crs must be EPSG:4326; got {src.crs}"
        density = src.read(1)
        suitability = src.read(2)
    assert density.shape == small_aoi.cells_per_side()
    assert density.min() >= 0.0 and density.max() <= 1.0, (
        f"density must be in [0, 1]; got min={density.min()}, max={density.max()}"
    )
    # With rain=20 (above threshold) the patch must be active.
    assert suitability.sum() >= 1.0, "suitability must mark the active patch cell"

    # Sidecar must exist and have the right keys.
    sidecar_path = output.with_suffix(".json")
    assert sidecar_path.exists(), f"sidecar missing: {sidecar_path}"
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["contract_version"] == "1.0"
    assert sidecar["seed"] == 1
    assert sidecar["year"] == 2024
    assert sidecar["month"] == 6
    assert sidecar["band_names"] == ["density", "suitability"]


# -- CLI smoke -------------------------------------------------------------


def test_abm_run_help() -> None:
    """`abm_run --help` exits 0 and lists the required options."""
    result = runner.invoke(run_app, ["--help"])
    assert result.exit_code == 0, result.stdout
    for opt in ("--aoi", "--year", "--month", "--env", "--habitat", "--output"):
        assert opt in result.stdout, f"--help must list {opt}"


def test_abm_run_end_to_end_with_synthetic_files(
    small_aoi: AOI,
    one_patch_gpkg: gpd.GeoDataFrame,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive the Typer CLI end-to-end with a synthetic env COG and a 1-row gpkg."""
    # Write a synthetic 4-band env COG to disk.
    h, w = small_aoi.cells_per_side()
    transform = from_bounds(*small_aoi.bbox, w, h)
    env_arr = np.zeros((4, h, w), dtype=np.float32)
    env_arr[0, :, :] = 0.5   # water_frac
    env_arr[1, :, :] = 0.7   # rainfall (normalised; rain = 20 mm / cap)
    env_arr[2, :, :] = 0.7   # temp_suitability
    env_arr[3, :, :] = 0.5   # ndvi
    env_path = tmp_path / "env.tif"
    with rasterio.open(
        env_path, "w",
        driver="GTiff", dtype="float32", count=4, height=h, width=w,
        crs=small_aoi.crs, transform=transform, nodata=-9999.0,
        tiled=True, compress="deflate", blockxsize=128, blockysize=128,
    ) as dst:
        dst.write(env_arr)
        dst.set_band_description(1, "water_frac")
        dst.set_band_description(2, "rainfall")
        dst.set_band_description(3, "temp_suitability")
        dst.set_band_description(4, "ndvi")
    # Sidecar.
    sidecar = {
        "crs": small_aoi.crs,
        "transform": [float(x) for x in transform[:6]],
        "aoi_slug": small_aoi.slug,
        "scale": small_aoi.scale.value,
        "year": 2024, "month": 6,
        "generator_version": "m1-thin-0.1.0",
        "abm_params_hash": "sha256:pending",
        "contract_version": "1.0",
        "band_names": ["water_frac", "rainfall", "temp_suitability", "ndvi"],
    }
    (tmp_path / "env.json").write_text(json.dumps(sidecar, indent=2))
    # Habitat gpkg.
    habitat_path = tmp_path / "habitat.gpkg"
    one_patch_gpkg.to_file(habitat_path, driver="GPKG")
    # Output path.
    out_path = tmp_path / "state.tif"

    result = runner.invoke(
        run_app,
        [
            "--aoi", "test",
            "--bbox", "-0.05,-0.05,0.05,0.05",
            "--year", "2024", "--month", "6",
            "--env", str(env_path),
            "--habitat", str(habitat_path),
            "--output", str(out_path),
            "--days", "30",
            "--seed", "1",
        ],
    )
    assert result.exit_code == 0, f"CLI failed: {result.stdout}"
    assert out_path.exists(), f"state COG missing: {out_path}"
    with rasterio.open(out_path) as src:
        assert src.count == 2
        assert src.dtypes[0] == "float32"
        assert src.crs.to_epsg() == 4326
