"""M6 & M7.4 — Load real ABM state from rollout snapshots (vector + transmission).

Picks the snapshot closest to the target month from runs directory or AOI directory,
crops/resamples to the AOI bbox, and returns the (C, H, W) state tensor (2 or 6 channels).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

from mal_commonlib.aoi import AOI
from mal_commonlib.config import RUNS_DIR


def load_abm_state(
    aoi: AOI,
    month: int = 1,
    rollout_dir: str | Path | None = None,
    seed: int = 1,
    include_transmission: bool = True,
) -> np.ndarray:
    """Load ABM state for the given month, aligned to the AOI grid.

    Args:
        aoi: Target AOI.
        month: Target month (1-12). Picks snapshot at day = month*30 or closest available.
        rollout_dir: Path to rollout directory. Defaults to runs/<aoi.slug>/, runs/abm/, or runs/1year-50r/.
        seed: Rollout seed to use.
        include_transmission: If True, loads 4-band transmission raster and stacks with 2-band vector state.

    Returns:
        state: (C, H, W) float32, aligned to the AOI grid (C=6 if transmission present, else C=2).
    """
    candidate_dirs = []
    if rollout_dir:
        candidate_dirs.append(Path(rollout_dir))
    candidate_dirs.extend([
        RUNS_DIR / aoi.slug,
        RUNS_DIR / "abm",
        RUNS_DIR / "1year-50r",
        RUNS_DIR / f"{aoi.slug}_2years",
        RUNS_DIR / "test_gif_14d",
    ])

    state_file: Path | None = None
    target_day = min(730, max(1, month * 30))

    for rdir in candidate_dirs:
        if not rdir.exists():
            continue

        # Look for day snapshot
        candidates = sorted(rdir.glob(f"*{aoi.slug}*day*.tif")) + sorted(rdir.glob("*_day*.tif"))
        # Exclude transmission rasters from vector state candidates
        state_candidates = [p for p in candidates if "transmission" not in p.name]
        if not state_candidates:
            state_candidates = sorted(rdir.glob(f"*{aoi.slug}*seed*.tif")) + sorted(rdir.glob("*.tif"))
            state_candidates = [p for p in state_candidates if "transmission" not in p.name]

        if state_candidates:
            # Pick closest day
            best_diff = float("inf")
            best_cand = state_candidates[0]
            for cand in state_candidates:
                m = re.search(r"_day(\d+)", cand.name)
                d = int(m.group(1)) if m else 30
                diff = abs(d - target_day)
                if diff < best_diff:
                    best_diff = diff
                    best_cand = cand
            state_file = best_cand
            break

    if state_file is None:
        raise FileNotFoundError(f"No ABM snapshots found for AOI '{aoi.slug}' in candidate directories.")

    # Load vector state raster
    with rasterio.open(state_file) as src:
        state_full = src.read().astype(np.float32)
        src_crs = str(src.crs)
        src_transform = src.transform
        nodata = src.nodata

    if nodata is not None:
        state_full[state_full == nodata] = 0.0

    H, W = aoi.cells_per_side()
    dst_vector = np.zeros((state_full.shape[0], H, W), dtype=np.float32)

    dst_transform = rasterio.transform.from_bounds(
        aoi.bbox[0], aoi.bbox[1], aoi.bbox[2], aoi.bbox[3], W, H
    )

    for i in range(state_full.shape[0]):
        reproject(
            source=state_full[i],
            destination=dst_vector[i],
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=aoi.crs,
            resampling=Resampling.bilinear,
        )

    # If transmission requested, try finding corresponding transmission raster
    if include_transmission:
        # Check paired transmission file
        parent_dir = state_file.parent
        stem = state_file.stem
        trans_file = parent_dir / f"{stem}_transmission.tif"
        if not trans_file.exists():
            # Try replacing _dayNNN with _transmission_dayNNN
            m_day = re.search(r"_day(\d+)", stem)
            if m_day:
                day_str = m_day.group(1)
                t_cands = sorted(parent_dir.glob(f"*transmission*day{day_str}.tif"))
                if t_cands:
                    trans_file = t_cands[0]

        if not trans_file.exists():
            t_cands = sorted(parent_dir.glob("*transmission*.tif"))
            if t_cands:
                trans_file = t_cands[0]

        if trans_file and trans_file.exists():
            with rasterio.open(trans_file) as src_t:
                trans_full = src_t.read().astype(np.float32)
                t_crs = str(src_t.crs)
                t_transform = src_t.transform
                t_nodata = src_t.nodata
            if t_nodata is not None:
                trans_full[trans_full == t_nodata] = 0.0

            dst_trans = np.zeros((trans_full.shape[0], H, W), dtype=np.float32)
            for i in range(trans_full.shape[0]):
                reproject(
                    source=trans_full[i],
                    destination=dst_trans[i],
                    src_transform=t_transform,
                    src_crs=t_crs,
                    dst_transform=dst_transform,
                    dst_crs=aoi.crs,
                    resampling=Resampling.bilinear,
                )
            return np.concatenate([dst_vector, dst_trans], axis=0)

    return dst_vector
