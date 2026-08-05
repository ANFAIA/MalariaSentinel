"""D16: Suitability AUC scorer.

Validates the habitat suitability model against larval site occurrences
using presence-only AUC with bootstrap 95% CI.

The suitability field is a weighted overlay of normalized env layers
(water_frac, rainfall, temperature, ndvi, elevation) from the same
env NC the ABM reads. Occurrence points come from data/ghana_idit/occurrence.txt.

Target: lower 95% CI bound > 0.65 (AUC_CI_TARGET).
Based on: Mordecai et al. 2013 thermal response + MCE weighted overlay.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import numpy as np

from scorers.base import Scorer, ScorerResult

_REPO_ROOT = Path(__file__).resolve().parents[6]
OCCURRENCE_PATH = _REPO_ROOT / "data" / "ghana_idit" / "occurrence.txt"
ENV_NC_PATH = _REPO_ROOT / "data" / "ghana" / "ghana_regional_2024_2025_env.nc"

# AOI bounds (from mal_ghana_sim config — Ghana NMCP AOI)
AOI_W, AOI_E = -2.966805555532119, 0.787916666690601
AOI_S, AOI_N = 4.692916666659342, 9.792361111104462
DST_CRS = "EPSG:32630"

# Mordecai 2013 thermal response
T_OPT = 25.0
T_HALF_WIDTH = 8.0

# Suitability weights (same as mal_ghana_sim config)
WEIGHTS = {
    "water_frac": 0.35,
    "rainfall": 0.20,
    "water_temp_c": 0.20,
    "ndvi": 0.15,
}

# AUC thresholds
AUC_N_BACKGROUND = 10_000
AUC_BOOTSTRAP = 1000
AUC_CI_TARGET = 0.65


def _norm_minmax(a: np.ndarray) -> np.ndarray:
    lo = float(np.nanmin(a))
    hi = float(np.nanmax(a))
    if hi - lo < 1e-9:
        return np.zeros_like(a)
    return np.clip((a - lo) / (hi - lo), 0, 1)


def _temp_suitability(T: np.ndarray) -> np.ndarray:
    return np.clip(1.0 - ((T - T_OPT) / T_HALF_WIDTH) ** 2, 0.0, 1.0)


def _load_occurrences() -> tuple[np.ndarray, np.ndarray]:
    lats, lons = [], []
    with open(OCCURRENCE_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                la = float(row["decimalLatitude"])
                lo = float(row["decimalLongitude"])
                if -90 <= la <= 90 and -180 <= lo <= 180:
                    lats.append(la)
                    lons.append(lo)
            except (KeyError, ValueError, TypeError):
                continue
    return np.array(lats), np.array(lons)


def _in_aoi_mask(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    return (
        (lats >= AOI_S) & (lats <= AOI_N)
        & (lons >= AOI_W) & (lons <= AOI_E)
    )


def _compute_suitability(nc_path: Path) -> tuple[np.ndarray, Any]:
    """Compute suitability field from env NC. Returns (suit, transform)."""
    import xarray as xr
    import rasterio

    ds = xr.open_dataset(nc_path)
    # Use first timestep for static layers
    water_frac = ds["water_frac"].values[0].astype(np.float32)
    rainfall = ds["rainfall"].values[0].astype(np.float32)
    water_temp_c = ds["water_temp_c"].values[0].astype(np.float32)
    ndvi = ds["ndvi"].values[0].astype(np.float32)

    # Normalize each layer
    wf_norm = _norm_minmax(water_frac)
    rain_norm = _norm_minmax(rainfall)
    temp_norm = _temp_suitability(water_temp_c)
    ndvi_norm = _norm_minmax(ndvi)

    # Weighted overlay
    suit = (
        WEIGHTS["water_frac"] * wf_norm
        + WEIGHTS["rainfall"] * rain_norm
        + WEIGHTS["water_temp_c"] * temp_norm
        + WEIGHTS["ndvi"] * ndvi_norm
    )
    suit = np.clip(suit, 0, 1).astype(np.float32)

    # Build transform from NC coords
    y = ds["y"].values
    x = ds["x"].values
    res_y = abs(y[1] - y[0]) if len(y) > 1 else 0.01
    res_x = abs(x[1] - x[0]) if len(x) > 1 else 0.01
    from rasterio.transform import from_bounds
    transform = from_bounds(float(x.min()), float(y.min()),
                            float(x.max()), float(y.max()),
                            suit.shape[1], suit.shape[0])
    ds.close()
    return suit, transform


def _points_to_grid(lats, lons, transform, shape):
    """Map lon/lat to grid (row, col)."""
    from pyproj import Transformer
    from rasterio.transform import rowcol

    t = Transformer.from_crs("EPSG:4326", DST_CRS, always_xy=True)
    xs, ys = t.transform(lons, lats)
    rows, cols = rowcol(transform, xs, ys)
    rows = np.asarray(rows)
    cols = np.asarray(cols)
    H, W = shape
    mask = (rows >= 0) & (rows < H) & (cols >= 0) & (cols < W)
    return rows[mask], cols[mask]


def _auc_with_ci(suit: np.ndarray, transform, site_lats, site_lons,
                 n_bg=AUC_N_BACKGROUND, n_boot=AUC_BOOTSTRAP, seed=0):
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(seed)
    pts = np.unique(np.stack([site_lats, site_lons], axis=1), axis=0)
    site_lats, site_lons = pts[:, 0], pts[:, 1]
    H, W = suit.shape

    site_rows, site_cols = _points_to_grid(site_lats, site_lons, transform, (H, W))
    if len(site_rows) == 0:
        return dict(auc=0.0, ci_low=0.0, ci_high=0.0, n_sites=0)

    site_vals = suit[site_rows, site_cols]
    bg_rows = rng.integers(0, H, n_bg)
    bg_cols = rng.integers(0, W, n_bg)
    bg_vals = suit[bg_rows, bg_cols]

    y = np.concatenate([np.ones(len(site_vals)), np.zeros(n_bg)])
    s = np.concatenate([site_vals, bg_vals])
    point = float(roc_auc_score(y, s))

    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(s), len(s))
        try:
            boots.append(roc_auc_score(y[idx], s[idx]))
        except ValueError:
            continue
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return dict(auc=point, ci_low=float(lo), ci_high=float(hi), n_sites=len(site_vals))


class SuitabilityAUCScorer(Scorer):
    """D16: Suitability AUC vs larval site occurrences."""

    @property
    def name(self) -> str:
        return "D16_suitability_auc"

    @property
    def weight(self) -> float:
        return 2.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        if not ENV_NC_PATH.is_file():
            return ScorerResult(
                score=0.0, value=0.0, target=f"lower CI > {AUC_CI_TARGET}",
                diagnostics={"error": f"env NC not found: {ENV_NC_PATH}"},
                passed=False,
            )
        if not OCCURRENCE_PATH.is_file():
            return ScorerResult(
                score=0.0, value=0.0, target=f"lower CI > {AUC_CI_TARGET}",
                diagnostics={"error": f"occurrence file not found: {OCCURRENCE_PATH}"},
                passed=False,
            )

        try:
            suit, transform = _compute_suitability(ENV_NC_PATH)
        except Exception as e:
            return ScorerResult(
                score=0.0, value=0.0, target=f"lower CI > {AUC_CI_TARGET}",
                diagnostics={"error": f"failed to compute suitability: {e}"},
                passed=False,
            )

        lats, lons = _load_occurrences()
        in_aoi = _in_aoi_mask(lats, lons)
        site_lats, site_lons = lats[in_aoi], lons[in_aoi]

        if len(site_lats) == 0:
            return ScorerResult(
                score=0.0, value=0.0, target=f"lower CI > {AUC_CI_TARGET}",
                diagnostics={"error": "no occurrence sites in AOI"},
                passed=False,
            )

        res = _auc_with_ci(suit, transform, site_lats, site_lons)

        # Score: 1.0 if lower CI > target, Gaussian decay otherwise
        if res["ci_low"] >= AUC_CI_TARGET:
            raw_score = 1.0
        else:
            raw_score = float(math.exp(-((res["ci_low"] - AUC_CI_TARGET) / 0.15) ** 2))

        return ScorerResult(
            score=round(raw_score, 4),
            value=round(res["auc"], 4),
            target=f"lower CI > {AUC_CI_TARGET}",
            diagnostics={
                "auc": round(res["auc"], 4),
                "ci_low": round(res["ci_low"], 4),
                "ci_high": round(res["ci_high"], 4),
                "n_sites": res["n_sites"],
                "n_total_occurrences": int(len(lats)),
                "n_in_aoi": int(in_aoi.sum()),
            },
            passed=res["ci_low"] >= AUC_CI_TARGET,
        )
