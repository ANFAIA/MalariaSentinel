"""Tests for the adapted prediction pipeline and model registry (M6 & M7.4)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

from mal_commonlib.aoi import Scale, AOI
from mal_core.prediction import (
    ModelRegistry,
    ModelManifest,
    DummyModel,
    run_prediction,
    get_latest_prediction,
    get_prediction_metadata,
    make_aoi,
)
from mal_core.prediction.state_loader import load_abm_state
from mal_core.prediction.env_loader import load_env_stack


def test_model_registry_dummy_load():
    reg = ModelRegistry()
    model = reg.load("dummy")
    assert isinstance(model, DummyModel)

    state = np.zeros((6, 64, 64), dtype=np.float32)
    env = np.zeros((4, 64, 64), dtype=np.float32)
    pred = model.predict(state, env)
    assert pred.shape == (6, 64, 64)


def test_state_loader_fallback_and_shape():
    aoi = make_aoi("ghana", Scale.REGIONAL)
    h, w = aoi.cells_per_side()

    state = load_abm_state(aoi, month=1, include_transmission=True)
    # Should align with AOI dimensions
    assert state.shape[-2] == h
    assert state.shape[-1] == w
    assert state.shape[0] in (2, 6)


def test_env_loader_shape():
    aoi = make_aoi("ghana", Scale.REGIONAL)
    h, w = aoi.cells_per_side()

    env = load_env_stack(aoi)
    assert env.shape == (4, h, w)


def test_run_prediction_end_to_end(tmp_path: Path):
    out_path = run_prediction(
        aoi_slug="ghana",
        scale=Scale.REGIONAL,
        year=2026,
        month=6,
        model_name="dummy",
        output_dir=tmp_path,
    )

    assert out_path.exists()
    sidecar = out_path.with_suffix(".tif.json")
    assert sidecar.exists()

    with open(sidecar) as f:
        meta = json.load(f)
    assert meta["aoi_slug"] == "ghana"
    assert meta["year"] == 2026
    assert meta["month"] == 6
    assert "bands" in meta

    with rasterio.open(out_path) as src:
        assert src.count >= 1
        assert src.crs is not None
