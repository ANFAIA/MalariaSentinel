"""Prediction pipeline — load model, run inference, write GeoTIFF output.

Orchestrates:
1. Load model from registry
2. Load or generate input state + env tensors
3. Run inference (model.predict)
4. Save output as GeoTIFF following the output contract v1.1
5. Return path to output
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds

from mal_commonlib.aoi import Scale
from mal_commonlib.config import RUNS_DIR

from .aoi import get_aggregator, grid_shape, make_aoi
from .env import ENV_CHANNELS, load_env_stack
from .registry import ModelRegistry
from .scenario import ScenarioConfig, interventions_to_params
from .state import load_abm_state


def _generate_dummy_inputs(h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
    state = np.zeros((2, h, w), dtype=np.float32)
    env = np.zeros((ENV_CHANNELS, h, w), dtype=np.float32)
    return state, env


def _load_real_inputs(aoi, month: int) -> tuple[np.ndarray, np.ndarray]:
    """Load real ABM state and env stack for the given AOI and month."""
    try:
        state = load_abm_state(aoi, month=month)
    except FileNotFoundError:
        state = np.zeros((2, aoi.cells_per_side()[0], aoi.cells_per_side()[1]), dtype=np.float32)
    try:
        env = load_env_stack(aoi)
    except Exception:
        h, w = aoi.cells_per_side()
        env = np.zeros((ENV_CHANNELS, h, w), dtype=np.float32)
    return state, env


def run_prediction(
    aoi_slug: str,
    scale: Scale,
    year: int,
    month: int = 1,
    model_name: str = "dummy",
    model_version: str | None = None,
    scenario: ScenarioConfig | None = None,
    output_dir: Path | None = None,
) -> Path:
    aoi = make_aoi(aoi_slug, scale)
    h, w = grid_shape(aoi)

    registry = ModelRegistry()
    model = registry.load(model_name, model_version)

    # Use real ABM state + env stack; fall back to zeros if unavailable.
    state, env = _load_real_inputs(aoi, month)

    if scenario is not None:
        params = interventions_to_params(scenario)

    prediction = model.predict(state, env)

    aggregator = get_aggregator(scale)
    aggregated = aggregator.aggregate(prediction, aoi)

    out_dir = output_dir or (RUNS_DIR / "predictions")
    out_dir.mkdir(parents=True, exist_ok=True)

    fname = f"{aoi_slug}_{scale.value}_{year}_{month:02d}_risk.tif"
    out_path = out_dir / fname

    w_res = (aoi.bbox[2] - aoi.bbox[0]) / max(w, 1)
    h_res = (aoi.bbox[3] - aoi.bbox[1]) / max(h, 1)
    transform = from_bounds(aoi.bbox[0], aoi.bbox[1], aoi.bbox[2], aoi.bbox[3], w, h)

    if aggregated.ndim == 0:
        aggregated = aggregated.reshape(1, 1)
    if aggregated.ndim == 1:
        side = int(np.ceil(np.sqrt(aggregated.size)))
        padded = np.zeros((side, side), dtype=np.float32)
        padded.flat[: aggregated.size] = aggregated
        aggregated = padded
    if aggregated.ndim == 2:
        aggregated = aggregated[np.newaxis]

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": aggregated.shape[0],
        "height": aggregated.shape[-2],
        "width": aggregated.shape[-1],
        "crs": aoi.crs,
        "transform": transform,
        "nodata": -9999.0,
        "tiled": True,
        "compress": "deflate",
        "blockxsize": 128,
        "blockysize": 128,
    }
    with rasterio.open(str(out_path), "w", **profile) as dst:
        dst.write(aggregated.astype(np.float32))
        dst.set_band_description(1, "risk")

    sidecar = {
        "crs": aoi.crs,
        "transform": list(transform)[:6],
        "aoi_slug": aoi_slug,
        "scale": scale.value,
        "year": year,
        "month": month,
        "model_name": model_name,
        "model_version": model_version or "latest",
        "contract_version": "1.1",
        "generator_version": "mal-execution-0.1.0",
    }
    sidecar_path = out_path.with_suffix(".tif.json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2))

    return out_path


def get_latest_prediction(aoi_slug: str) -> Path | None:
    pred_dir = RUNS_DIR / "predictions"
    if not pred_dir.exists():
        return None
    matches = sorted(pred_dir.glob(f"{aoi_slug}_*_risk.tif"))
    return matches[-1] if matches else None


def get_prediction_metadata(aoi_slug: str) -> dict | None:
    latest = get_latest_prediction(aoi_slug)
    if latest is None:
        return None
    sidecar_path = latest.with_suffix(".tif.json")
    if sidecar_path.exists():
        return json.loads(sidecar_path.read_text())
    return {"path": str(latest)}
