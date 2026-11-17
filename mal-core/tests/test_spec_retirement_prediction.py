"""Checks migrated from the retired prediction specification.

The spec is gone; the facts live in the code and in this file. See
docs/plans/in-process/spec-retirement-ledger.md for the row that maps
each assertion to this test.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
import yaml

from mal_commonlib.aoi import Scale
from mal_core.prediction.aggregator import (
    SCALE_GRIDS,
    ContinentalAggregator,
    NationalAggregator,
    RegionalAggregator,
    get_aggregator,
    grid_shape,
    make_aoi,
)
from mal_core.prediction.env_loader import ENV_CHANNEL_ORDER
from mal_core.prediction.predictor import run_prediction
from mal_core.prediction.registry import DummyModel, ModelManifest, ModelRegistry


# ---------------------------------------------------------------------------
# INV-2: the env channel order
# ---------------------------------------------------------------------------

def test_env_channel_order_is_the_contract_v3_set():
    assert ENV_CHANNEL_ORDER == ["rainfall", "air_temp_c", "jrc_persistent",
                                 "lc_wetland"]


# ---------------------------------------------------------------------------
# INV-4 / INV-5 / INV-6: the model registry
# ---------------------------------------------------------------------------

def test_model_manifest_defaults():
    manifest = ModelManifest(name="x", version="v1")
    assert manifest.contract_version == "1.1"
    assert manifest.in_channels == 10
    assert manifest.out_channels == 6
    assert manifest.checkpoint == ""


def test_registry_discovers_model_yaml_manifests(tmp_path):
    model_dir = tmp_path / "unet-ghana_1.0"
    model_dir.mkdir(parents=True)
    (model_dir / "model.yaml").write_text(yaml.safe_dump({
        "name": "unet-ghana", "version": "1.0", "contract_version": "1.1",
        "in_channels": 10, "out_channels": 6, "checkpoint": "",
        "description": "test",
    }))
    registry = ModelRegistry(models_dir=tmp_path)
    assert "unet-ghana@1.0" in registry.scan()
    model = registry.load("unet-ghana")
    assert isinstance(model, DummyModel)


def test_registry_picks_the_latest_version(tmp_path):
    for version in ("1.0", "1.1"):
        d = tmp_path / f"unet-ghana_{version}"
        d.mkdir(parents=True)
        (d / "model.yaml").write_text(yaml.safe_dump({
            "name": "unet-ghana", "version": version, "checkpoint": "",
        }))
    registry = ModelRegistry(models_dir=tmp_path)
    registry.scan()
    assert registry.get("unet-ghana").manifest.version == "1.1"


def test_dummy_model_returns_zeros_with_the_state_channel_count():
    out = DummyModel().predict(np.zeros((6, 32, 32), dtype=np.float32),
                               np.zeros((4, 32, 32), dtype=np.float32))
    assert out.shape == (6, 32, 32)
    assert not out.any()


# ---------------------------------------------------------------------------
# INV-7 / INV-8 / INV-9: the aggregators
# ---------------------------------------------------------------------------

def test_regional_aggregator_is_a_passthrough():
    aoi = make_aoi("ghana", Scale.REGIONAL)
    raster = np.random.RandomState(0).rand(2, 128, 128).astype("float32")
    assert RegionalAggregator().aggregate(raster, aoi).shape == raster.shape


def test_national_aggregator_pools_by_ten():
    aoi = make_aoi("ghana", Scale.NATIONAL)
    raster = np.random.RandomState(0).rand(2, 128, 128).astype("float32")
    out = NationalAggregator().aggregate(raster, aoi)
    assert out.ndim == 3
    assert out.shape == (2, 128 // 10, 128 // 10)


def test_continental_aggregator_returns_one_scalar():
    aoi = make_aoi("ghana", Scale.CONTINENTAL)
    raster = np.random.RandomState(0).rand(2, 128, 128).astype("float32")
    out = ContinentalAggregator().aggregate(raster, aoi)
    assert out.shape == (1,)
    assert out[0] == pytest.approx(float(raster.mean()))


def test_scale_grids_are_the_documented_resolutions():
    assert SCALE_GRIDS[Scale.REGIONAL].resolution_m == 1000
    assert SCALE_GRIDS[Scale.NATIONAL].resolution_m == 2000
    assert SCALE_GRIDS[Scale.CONTINENTAL].resolution_m == 5000
    for grid in SCALE_GRIDS.values():
        assert grid.tile_size == 128


def test_get_aggregator_maps_every_scale():
    for scale, expected in (
        (Scale.REGIONAL, RegionalAggregator),
        (Scale.NATIONAL, NationalAggregator),
        (Scale.CONTINENTAL, ContinentalAggregator),
    ):
        assert isinstance(get_aggregator(scale), expected)


def test_grid_shape_comes_from_the_aoi():
    aoi = make_aoi("ghana", Scale.REGIONAL)
    assert grid_shape(aoi) == aoi.cells_per_side()


# ---------------------------------------------------------------------------
# INV-12 / INV-13 / INV-14 / INV-15 / INV-16: the emitted risk raster
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def prediction(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("predictions")
    path = run_prediction("ghana", Scale.REGIONAL, year=2024, month=7,
                          output_dir=out_dir)
    return path, out_dir


def test_output_file_name_follows_the_convention(prediction):
    path, _ = prediction
    assert path.name == "ghana_regional_2024_07_risk.tif"


def test_the_sidecar_uses_the_tif_json_suffix(prediction):
    path, _ = prediction
    sidecar = path.with_suffix(".tif.json")
    assert sidecar.exists(), sorted(p.name for p in path.parent.iterdir())
    payload = json.loads(sidecar.read_text())
    for key in ("crs", "transform", "aoi_slug", "scale", "year", "month",
                "model_name", "model_version", "contract_version",
                "generator_version"):
        assert key in payload, f"the sidecar is missing {key!r}"
    assert payload["aoi_slug"] == "ghana"
    assert payload["scale"] == "regional"
    assert payload["year"] == 2024
    assert payload["month"] == 7
    assert payload["contract_version"] == "1.1"
    assert len(payload["transform"]) == 6


def test_the_risk_raster_carries_the_documented_profile(prediction):
    path, _ = prediction
    with rasterio.open(path) as src:
        assert src.dtypes[0] == "float32"
        assert src.nodata == -9999.0
        assert src.profile.get("compress") == "deflate"
        assert src.profile.get("tiled") is True
        assert src.descriptions[0] in (
            "predicted_risk",
            "predicted_adult_patch_count",
        )


def test_the_prediction_state_loader_day_is_clamped_to_the_code_range():
    """The retired spec said [7, 360]; the code clamps to [1, 730]."""
    from mal_core.prediction import state_loader

    source = Path(state_loader.__file__).read_text(encoding="utf-8")
    assert "min(730, max(1, month * 30))" in source
