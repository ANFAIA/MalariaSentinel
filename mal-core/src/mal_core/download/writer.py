"""Writer module — persists loader return values to data/<aoi>/."""
from __future__ import annotations
import logging
from pathlib import Path

import xarray as xr
import rioxarray  # noqa: F401 — registers .rio accessor

log = logging.getLogger(__name__)


def save_product(data: xr.DataArray | xr.Dataset, path: Path, format: str | None = None, var_name: str | None = None) -> Path:
    """Save a loader return value to disk.

    Args:
        data: DataArray or Dataset to save.
        path: output file path.
        format: explicit format hint ("tif" | "nc"). If None, infers from
                isinstance(data, xr.Dataset) → nc, else → tif.
        var_name: variable name for NetCDF DataArray (e.g. "rainfall").
                  If None, uses path.stem.

    Returns the path that was written.

    Raises ValueError if a 3D DataArray is passed with format="tif".
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if format is None:
        format = "nc" if isinstance(data, xr.Dataset) else "tif"

    if format == "tif":
        # Guard: 3D DataArrays cannot be written as TIF
        if isinstance(data, xr.DataArray) and data.ndim == 3:
            raise ValueError(
                f"3D DataArray (shape {data.shape}) requires NC writer, not TIF. "
                f"Use format='nc' or save as xr.Dataset."
            )
        data.rio.to_raster(str(path))
        log.info("Saved raster → %s", path)
    elif format == "nc":
        if isinstance(data, xr.Dataset):
            data.to_netcdf(path)
        else:
            # DataArray → Dataset for NetCDF
            name = var_name or path.stem
            ds = data.to_dataset(name=name)
            ds.to_netcdf(path)
        log.info("Saved dataset → %s", path)
    else:
        raise ValueError(f"Unknown format: {format!r}. Expected 'tif' or 'nc'.")

    return path
