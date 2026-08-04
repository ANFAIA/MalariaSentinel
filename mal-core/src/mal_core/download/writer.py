"""Writer module — persists loader return values to data/<aoi>/."""
from __future__ import annotations
import logging
from pathlib import Path

import xarray as xr
import rioxarray  # noqa: F401 — registers .rio accessor

log = logging.getLogger(__name__)


def save_product(data: xr.DataArray | xr.Dataset, path: Path) -> Path:
    """Save a loader return value to disk.

    - xr.DataArray → GeoTIFF (.tif) via rioxarray
    - xr.Dataset → NetCDF (.nc) via xarray

    Returns the path that was written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, xr.Dataset):
        data.to_netcdf(path)
        log.info("Saved dataset → %s", path)
    else:
        data.rio.to_raster(str(path))
        log.info("Saved raster → %s", path)
    return path
