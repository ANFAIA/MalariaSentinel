"""Writer module — persists loader return values to data/<aoi>/."""
from __future__ import annotations
import logging
from pathlib import Path

import xarray as xr
import rioxarray  # noqa: F401 — registers .rio accessor

log = logging.getLogger(__name__)


def save_product(
    data: xr.DataArray | xr.Dataset,
    path: Path,
    *,
    format: str | None = None,
) -> Path:
    """Save a loader return value to disk.

    Parameters
    ----------
    data:
        The xarray object to persist.
    path:
        Destination file path.
    format:
        Explicit output format override.  Accepted values:

        * ``"tif"``  – force GeoTIFF via rioxarray.
        * ``"nc"``   – force NetCDF via xarray.
        * ``None``   – auto-detect (default): Dataset → NetCDF, DataArray → GeoTIFF.

    Raises
    ------
    ValueError
        If *format* is ``"tif"`` but *data* is a 3-D DataArray (rasterio
        cannot write multi-band time-series to a single TIF).

    Returns the path that was written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # ── explicit format override ────────────────────────────────────────
    if format == "nc":
        data.to_netcdf(str(path))
        log.info("Saved (explicit nc) → %s", path)
        return path

    if format == "tif":
        if isinstance(data, xr.Dataset):
            raise ValueError("Cannot write Dataset as TIF. Pass format='nc' or use a DataArray.")
        if data.ndim > 2:
            raise ValueError(
                f"3D DataArray requires NC writer, not TIF writer. "
                f"Pass format='nc' or use a 2D slice.  Got {data.ndim}D with dims {data.dims}."
            )
        data.rio.to_raster(str(path))
        log.info("Saved (explicit tif) → %s", path)
        return path

    # ── auto-detect (backward compat) ───────────────────────────────────
    if isinstance(data, xr.Dataset):
        data.to_netcdf(path)
        log.info("Saved dataset → %s", path)
    else:
        data.rio.to_raster(str(path))
        log.info("Saved raster → %s", path)
    return path
