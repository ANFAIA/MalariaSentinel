"""End-to-end test for the M1.5 ``AnophelesABM`` facade.

The facade wires the ``CoordinatorModel`` and ``MosquitoSubmodel``
together and exposes the M1.4 ``AnophelesABM`` public API
(``__init__``, ``step``, ``snapshot``). This test exercises the
full pipeline end-to-end:

  * Construct the facade with a 100-patch synthetic gpkg.
  * Seed ~30k mosquito agents (100 patches * 1000 K * 0.3 init_frac).
  * Run 30 days.
  * Write the state COG via ``facade.snapshot(...)``.
  * Validate the COG (2 bands, float32, EPSG:4326, sidecar JSON).

The test also measures wall-clock time so we can track the M1.5
performance budget (target: < 60 s on 30k patches + 9M agents; < 5 s
on 100 patches + 30k agents on the CI machine).
"""
from __future__ import annotations

import json
import pathlib
import time
from datetime import date

import geopandas as gpd
import numpy as np
import polars as pl
import pytest
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import Point

from mal_commonlib.aoi import AOI, Scale

from mal_ghana_sim.abm import AnophelesABM
from mal_ghana_sim.abm.habitat import HabitatType


# -- fixtures --------------------------------------------------------------


@pytest.fixture
def aoid() -> AOI:
    """A 0.5 deg x 0.5 deg AOI (50x50 at 1km resolution) for fast tests."""
    return AOI.from_bbox(
        -0.25, -0.25, 0.25, 0.25,
        crs="EPSG:4326", slug="test", resolution_m=1000, scale=Scale.REGIONAL,
    )


@pytest.fixture
def hundred_patch_gpkg(aoid: AOI) -> gpd.GeoDataFrame:
    """A 100-patch gpkg scattered on a 10x10 grid (centres of 10x10 cells)."""
    h, w = aoid.cells_per_side()
    transform = from_bounds(*aoid.bbox, w, h)
    # Use the centre 10x10 cells.
    rs = []
    cs = []
    for r in range(h // 2 - 5, h // 2 + 5):
        for c in range(w // 2 - 5, w // 2 + 5):
            rs.append(r)
            cs.append(c)
    assert len(rs) == 100
    xs = transform.c + (np.array(cs) + 0.5) * transform.a
    ys = transform.f + (np.array(rs) + 0.5) * transform.e
    return gpd.GeoDataFrame(
        {
            "hab_type": [HabitatType.PLUVIAL_POOL.value] * 100,
            "twi_value": list(range(100)),
            "water_frac_value": [0.5] * 100,
            "K": [1000] * 100,
            "row": rs,
            "col": cs,
            "aoi_slug": [aoid.slug] * 100,
        },
        geometry=[Point(float(x), float(y)) for x, y in zip(xs, ys)],
        crs=aoid.crs,
    )


def _synthetic_env(rain: float = 20.0, temp: float = 25.0) -> dict:
    return {
        "rain_daily": lambda d, lon, lat: rain,
        "water_temp_c": lambda d, lon, lat: temp,
        "water_frac": lambda d, lon, lat: 0.5,
        "ndvi": lambda d, lon, lat: 0.5,
    }


# -- e2e ------------------------------------------------------------------


def test_facade_construction_seeds_population(
    aoid: AOI, hundred_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """The facade seeds the submodel with ``n_patches * K * init_frac`` agents."""
    m = AnophelesABM(
        aoid, _synthetic_env(), hundred_patch_gpkg,
        seed=1, start_date=date(2024, 6, 1),
    )
    expected = int(round(100 * m.K_MAX * 0.3))
    assert m.submodel.total_agents() == expected
    # The coordinator has 100 patches.
    assert len(m.coordinator.habitat_engine.patches) == 100
    # And the cell lookup has 100 entries.
    assert len(m.coordinator._cell_lookup) == 100


def test_facade_30_day_rollout_writes_cog(
    aoid: AOI, hundred_patch_gpkg: gpd.GeoDataFrame, tmp_path: pathlib.Path,
) -> None:
    """30-day rollout + snapshot writes a valid 2-band state COG."""
    m = AnophelesABM(
        aoid, _synthetic_env(rain=20.0, temp=25.0), hundred_patch_gpkg,
        seed=1, start_date=date(2024, 6, 1),
    )
    n_initial = m.submodel.total_agents()
    t0 = time.perf_counter()
    for _ in range(30):
        m.step()
    elapsed = time.perf_counter() - t0
    # Performance budget: < 30 s on 100 patches + 30k agents on the CI machine.
    # On the target Hetzner the 30k-patch / 9M-agent rollout is the
    # one that must be < 60 s; this test is the cheap proxy.
    assert elapsed < 30.0, (
        f"30-day rollout with 100 patches + 30k agents took {elapsed:.2f}s; "
        f"expected < 30s on the CI machine"
    )
    n_after = m.submodel.total_agents()
    # Population should be non-zero after 30 days of active patches.
    assert n_after > 0
    # Snapshot writes the state COG.
    out = tmp_path / "state.tif"
    m.snapshot(str(out), year=2024, month=6, seed=1)
    assert out.exists()
    with rasterio.open(out) as src:
        assert src.count == 2
        assert src.dtypes[0] == "float32"
        assert src.crs.to_epsg() == 4326
        density = src.read(1)
        suitability = src.read(2)
    h, w = aoid.cells_per_side()
    assert density.shape == (h, w)
    assert density.min() >= 0.0 and density.max() <= 1.0
    # M2 fix: band 1 (suitability) is per-cell adult density / K_MAX,
    # not the v1 "1.0 for cells with active patch" binary map. With
    # rain=20 the patches are all active and after 30 days adults
    # have emerged; we expect at least the 100 patch cells to be
    # non-zero (some adults will have dispersed into adjacent cells,
    # which is exactly the M2 behaviour the new band is meant to
    # surface).
    assert int((suitability > 0.0).sum()) >= 100, (
        f"expected >= 100 cells with adult density > 0; got "
        f"{int((suitability > 0.0).sum())}"
    )
    assert suitability.min() >= 0.0 and suitability.max() <= 1.0
    # The mean suitability across the AOI should be small (adults
    # are mostly clustered at the patches, not spread uniformly).
    assert float(suitability.mean()) < 0.5
    # And the sidecar must exist with the right shape.
    sidecar = json.loads(out.with_suffix(".json").read_text())
    assert sidecar["contract_version"] == "1.0"
    assert sidecar["year"] == 2024
    assert sidecar["month"] == 6
    assert sidecar["seed"] == 1
    assert sidecar["band_names"] == ["density", "suitability"]
    # And the generator version reflects the M1.5 architecture.
    assert sidecar["generator_version"] == "m1.5-mesa-frames+polars"


def test_facade_backward_compat_attributes(
    aoid: AOI, hundred_patch_gpkg: gpd.GeoDataFrame,
) -> None:
    """The facade exposes the M1.4 attributes tests + scripts depend on."""
    m = AnophelesABM(
        aoid, _synthetic_env(), hundred_patch_gpkg,
        seed=42, start_date=date(2024, 6, 1),
    )
    # Backward-compat shims (M1.4 code paths and tests).
    assert m.aoi is aoid
    assert m.env is not None
    assert m.current_date == date(2024, 6, 1)
    assert m.rng is not None
    assert hasattr(m.rng, "integers")  # numpy Generator
    assert m.schedule is m.coordinator.schedule
    assert m.habitat_engine is m.coordinator.habitat_engine
    assert m.climate is m.coordinator.climate
    assert m.geospace is m.coordinator.geospace
    # New M1.5 attributes.
    assert m.coordinator is not None
    assert m.submodel is not None
    assert isinstance(m.submodel.df, pl.DataFrame)


def test_facade_determinism_same_seed_same_cog(
    aoid: AOI, hundred_patch_gpkg: gpd.GeoDataFrame, tmp_path: pathlib.Path,
) -> None:
    """Two facades with the same seed produce identical state COGs."""
    out1 = tmp_path / "state1.tif"
    out2 = tmp_path / "state2.tif"
    m1 = AnophelesABM(
        aoid, _synthetic_env(rain=20.0, temp=25.0), hundred_patch_gpkg,
        seed=42, start_date=date(2024, 6, 1),
    )
    for _ in range(30):
        m1.step()
    m1.snapshot(str(out1), year=2024, month=6, seed=42)
    m2 = AnophelesABM(
        aoid, _synthetic_env(rain=20.0, temp=25.0), hundred_patch_gpkg,
        seed=42, start_date=date(2024, 6, 1),
    )
    for _ in range(30):
        m2.step()
    m2.snapshot(str(out2), year=2024, month=6, seed=42)
    with rasterio.open(out1) as s1, rasterio.open(out2) as s2:
        d1 = s1.read(1)
        d2 = s2.read(1)
    np.testing.assert_array_equal(d1, d2)
