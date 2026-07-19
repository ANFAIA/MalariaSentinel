"""SDSS AOI/scale abstraction — grid definitions and aggregation per scale.

Wraps ``mal_commonlib.aoi.AOI`` / ``Scale`` and adds:
- per-scale grid definitions (resolution, tile size)
- aggregation logic (raw raster, GADM-2 mean-pool, GADM-0 scalars)
- AOI catalogue (known AOIs with their default parameters)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from mal_commonlib.aoi import AOI, Scale


@dataclass(frozen=True)
class GridDef:
    resolution_m: int
    tile_size: int
    description: str


SCALE_GRIDS: dict[Scale, GridDef] = {
    Scale.REGIONAL: GridDef(1000, 128, "1 km raster, no aggregation"),
    Scale.NATIONAL: GridDef(2000, 128, "GADM-2 mean-pool (district level)"),
    Scale.CONTINENTAL: GridDef(5000, 128, "5 km + GADM-0 scalars (country level)"),
}


AOI_CATALOGUE: dict[str, dict] = {
    "ghana": {
        "name": "Ghana NMCP AOI",
        "bbox": (-2.966805555532119, 4.692916666659342, 0.787916666690601, 9.792361111104462),
        "crs": "EPSG:4326",
        "gadm_id": "GHA",
    },
}


def make_aoi(slug: str, scale: Scale) -> AOI:
    if slug not in AOI_CATALOGUE:
        raise KeyError(f"Unknown AOI {slug!r}. Known: {list(AOI_CATALOGUE)}")
    entry = AOI_CATALOGUE[slug]
    grid = SCALE_GRIDS[scale]
    return AOI(
        slug=slug,
        name=entry["name"],
        bbox=entry["bbox"],
        crs=entry["crs"],
        resolution_m=grid.resolution_m,
        scale=scale,
        gadm_id=entry.get("gadm_id"),
    )


class Aggregator(Protocol):
    def aggregate(self, raster: np.ndarray, aoi: AOI) -> np.ndarray: ...


class RegionalAggregator:
    def aggregate(self, raster: np.ndarray, aoi: AOI) -> np.ndarray:
        return raster


class NationalAggregator:
    def aggregate(self, raster: np.ndarray, aoi: AOI) -> np.ndarray:
        h, w = raster.shape[-2:]
        n_rows, n_cols = max(1, h // 10), max(1, w // 10)
        block_h = h // n_rows
        block_w = w // n_cols
        trimmed = raster[..., : block_h * n_rows, : block_w * n_cols]
        reshaped = trimmed.reshape(
            *raster.shape[:-2], n_rows, block_h, n_cols, block_w
        )
        return reshaped.mean(axis=(-3, -1))


class ContinentalAggregator:
    def aggregate(self, raster: np.ndarray, aoi: AOI) -> np.ndarray:
        return np.array([float(raster.mean())])


def get_aggregator(scale: Scale) -> Aggregator:
    return {
        Scale.REGIONAL: RegionalAggregator(),
        Scale.NATIONAL: NationalAggregator(),
        Scale.CONTINENTAL: ContinentalAggregator(),
    }[scale]


def grid_shape(aoi: AOI) -> tuple[int, int]:
    h, w = aoi.cells_per_side()
    return h, w
