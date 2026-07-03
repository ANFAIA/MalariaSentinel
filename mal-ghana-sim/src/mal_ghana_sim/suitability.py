"""Stage 2 — suitability model -> carrying-capacity field K(cell).

Weighted overlay (Multi-Criteria Evaluation) of normalized env layers, with the
Mordecai et al. 2013 thermal response applied to temperature. Validated by
presence-only AUC with bootstrap 95% CI against the in-AOI larval sites.
"""
from __future__ import annotations

import csv

import numpy as np

from . import config as C
from .ingest import LAYER_ORDER


def load_occurrences() -> tuple[np.ndarray, np.ndarray]:
    """Return (lats, lons) of valid Ghana larval sites from occurrence.txt."""
    lats, lons = [], []
    with open(C.OCCURRENCE, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                la = float(row["decimalLatitude"]); lo = float(row["decimalLongitude"])
                if -90 <= la <= 90 and -180 <= lo <= 180:
                    lats.append(la); lons.append(lo)
            except (KeyError, ValueError, TypeError):
                continue
    return np.array(lats), np.array(lons)


def in_aoi_mask(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    return (
        (lats >= C.AOI_S) & (lats <= C.AOI_N) &
        (lons >= C.AOI_W) & (lons <= C.AOI_E)
    )


def _norm_minmax(a: np.ndarray) -> np.ndarray:
    lo = float(np.nanmin(a)); hi = float(np.nanmax(a))
    if hi - lo < 1e-9:
        return np.zeros_like(a)
    return np.clip((a - lo) / (hi - lo), 0, 1)


def suitability_from_stack(stack: np.ndarray, present: list[str]) -> np.ndarray:
    """Weighted overlay in [0,1]. Redistributes missing-layer weights over the present ones."""
    idx = {n: i for i, n in enumerate(LAYER_ORDER)}
    weights = {k: v for k, v in C.WEIGHTS.items() if k in present}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("no usable layers present in the stack")
    weights = {k: v / total for k, v in weights.items()}

    suit = np.zeros(stack.shape[1:], dtype=np.float32)
    for name, w in weights.items():
        a = stack[idx[name]]
        if name == "temperature":
            a = C.temp_suitability(a)   # thermal response, not raw deg C
        elif name == "elevation":
            a = 1.0 - _norm_minmax(a)   # INVERTED: lowland (water accumulation) = more suitable
        else:
            a = _norm_minmax(a)
        suit += w * a.astype(np.float32)
    return np.clip(suit, 0, 1)


def carrying_capacity(suit: np.ndarray, k_max: float = C.K_MAX) -> np.ndarray:
    return suit * k_max


# --- AUC + bootstrap 95% CI (Stage 2 validation) ---
def _points_to_grid(lats, lons, affine, crs=C.DST_CRS) -> np.ndarray:
    """Map lon/lat occurrence points (EPSG:4326) to grid (row,col) in a UTM grid."""
    from pyproj import Transformer
    from rasterio.transform import rowcol
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = t.transform(lons, lats)
    rows, cols = rowcol(affine, xs, ys)
    return np.stack([np.asarray(rows), np.asarray(cols)], axis=1)


def auc_with_ci(suit: np.ndarray, affine, site_lats, site_lons,
                n_bg=C.AUC_N_BACKGROUND, n_boot=C.AUC_BOOTSTRAP, seed=0):
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(seed)
    # dedup to unique presence locations (avoid clustered larvae overweighting the 24 sites)
    pts = np.unique(np.stack([site_lats, site_lons], axis=1), axis=0)
    site_lats, site_lons = pts[:, 0], pts[:, 1]
    H, W = suit.shape
    site_rc = _points_to_grid(site_lats, site_lons, affine)
    site_rc = site_rc[(site_rc[:, 0] >= 0) & (site_rc[:, 0] < H) &
                      (site_rc[:, 1] >= 0) & (site_rc[:, 1] < W)]
    site_vals = suit[site_rc[:, 0], site_rc[:, 1]]
    bg_rows = rng.integers(0, H, n_bg); bg_cols = rng.integers(0, W, n_bg)
    bg_vals = suit[bg_rows, bg_cols]
    y = np.concatenate([np.ones(len(site_vals)), np.zeros(n_bg)])
    s = np.concatenate([site_vals, bg_vals])
    point = float(roc_auc_score(y, s))
    # bootstrap
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(s), len(s))
        try:
            boots.append(roc_auc_score(y[idx], s[idx]))
        except ValueError:
            continue
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return dict(auc=point, ci_low=float(lo), ci_high=float(hi), n_sites=len(site_vals))
