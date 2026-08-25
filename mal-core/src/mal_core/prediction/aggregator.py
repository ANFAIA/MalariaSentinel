"""SDSS AOI/scale abstraction — grid definitions and aggregation per scale.

Wraps ``mal_commonlib.aoi.AOI`` / ``Scale`` and adds:
- per-scale grid definitions (resolution, tile size)
- aggregation logic (raw raster, GADM-2 mean-pool, GADM-0 scalars)
- ``make_aoi()``: scale-aware factory that reads from the YAML registry
"""
from __future__ import annotations

from dataclasses import dataclass
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


def make_aoi(slug: str, scale: Scale) -> AOI:
    """Build an AOI from the YAML registry, overriding resolution for the scale."""
    aoi = AOI.from_slug(slug)
    grid = SCALE_GRIDS[scale]
    return AOI(
        slug=aoi.slug,
        name=aoi.name,
        bbox=aoi.bbox,
        crs=aoi.crs,
        resolution_m=grid.resolution_m,
        scale=scale,
        gadm_id=aoi.gadm_id,
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
