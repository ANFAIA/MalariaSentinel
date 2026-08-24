"""M6 & M7.4 — Load real environmental stack from AOI data (NetCDF/GeoTIFF) or runs/env_stack.npz.

Selects the 4 channels the U-Net expects (water_frac, rainfall, temperature, ndvi),
and resamples to the AOI grid (EPSG:4326).
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

from mal_commonlib.aoi import AOI
from mal_commonlib.config import RUNS_DIR

ENV_CHANNELS = 4
ENV_CHANNEL_ORDER = ["water_frac", "rainfall", "water_temp_c", "temperature", "ndvi"]


def load_env_stack(aoi: AOI, env_path: str | Path | None = None) -> np.ndarray:
    """Load env stack and resample to the AOI grid.

    Args:
        aoi: Target AOI (defines bbox, CRS, grid shape).
        env_path: Optional explicit path to env NetCDF/GeoTIFF or env_stack.npz.

    Returns:
        env: (ENV_CHANNELS, H, W) float32, aligned to the AOI grid.
    """
    H, W = aoi.cells_per_side()
    dst_transform = rasterio.transform.from_bounds(
        aoi.bbox[0], aoi.bbox[1], aoi.bbox[2], aoi.bbox[3], W, H
    )

    # 1. Check if explicit env_path provided
    resolved_path: Path | None = None
    if env_path:
        resolved_path = Path(env_path)
    else:
        # Check data/<aoi.slug>/
        data_dir = Path("data") / aoi.slug
        if data_dir.exists():
            nc_cands = sorted(data_dir.glob("*_env.nc")) + sorted(data_dir.glob("*.nc"))
            tif_cands = sorted(data_dir.glob("*_env*.tif")) + sorted(data_dir.glob("*.tif"))
            if nc_cands:
                resolved_path = nc_cands[0]
            elif tif_cands:
                resolved_path = tif_cands[0]

    # 2. If path is a NetCDF file, read via xarray/rasterio
    if resolved_path and resolved_path.exists() and resolved_path.suffix in (".nc", ".nc4"):
        try:
            import xarray as xr
            with xr.open_dataset(resolved_path) as ds:
                vars_found = [v for v in ENV_CHANNEL_ORDER if v in ds]
                if vars_found:
                    arrs = []
                    for v in vars_found[:ENV_CHANNELS]:
                        vals = ds[v].values.squeeze()
                        if vals.ndim == 3:
                            vals = vals[0]
                        arrs.append(vals.astype(np.float32))
                    while len(arrs) < ENV_CHANNELS:
                        arrs.append(np.zeros_like(arrs[0]))
                    raw_stack = np.stack(arrs[:ENV_CHANNELS], axis=0)

                    # Reproject to AOI grid
                    dst = np.zeros((ENV_CHANNELS, H, W), dtype=np.float32)
                    src_transform = rasterio.transform.from_bounds(
                        aoi.bbox[0], aoi.bbox[1], aoi.bbox[2], aoi.bbox[3],
                        raw_stack.shape[-1], raw_stack.shape[-2]
                    )
                    for i in range(ENV_CHANNELS):
                        reproject(
                            source=raw_stack[i],
                            destination=dst[i],
                            src_transform=src_transform,
                            src_crs=aoi.crs,
                            dst_transform=dst_transform,
                            dst_crs=aoi.crs,
                            resampling=Resampling.bilinear,
                        )
                    return dst
        except Exception:
            pass

    # 3. If path is a GeoTIFF
    if resolved_path and resolved_path.exists() and resolved_path.suffix in (".tif", ".tiff"):
        try:
            with rasterio.open(resolved_path) as src:
                raw_stack = src.read().astype(np.float32)
                src_crs = str(src.crs)
                src_transform = src.transform
                nodata = src.nodata

            if nodata is not None:
                raw_stack[raw_stack == nodata] = 0.0

            if raw_stack.shape[0] < ENV_CHANNELS:
                padded = np.zeros((ENV_CHANNELS, raw_stack.shape[1], raw_stack.shape[2]), dtype=np.float32)
                padded[:raw_stack.shape[0]] = raw_stack
                raw_stack = padded

            dst = np.zeros((ENV_CHANNELS, H, W), dtype=np.float32)
            for i in range(ENV_CHANNELS):
                reproject(
                    source=raw_stack[i],
                    destination=dst[i],
                    src_transform=src_transform,
                    src_crs=src_crs,
                    dst_transform=dst_transform,
                    dst_crs=aoi.crs,
                    resampling=Resampling.bilinear,
                )
            return dst
        except Exception:
            pass

    # 4. Fallback: runs/env_stack.npz
    npz_path = RUNS_DIR / "env_stack.npz"
    if npz_path.exists():
        try:
            data = np.load(npz_path)
            stack = data["stack"]
            present = list(data["present"])
            src_crs = str(data["crs"])
            indices = [present.index(name) for name in ["water_frac", "rainfall", "temperature", "ndvi"] if name in present]
            if len(indices) != ENV_CHANNELS:
                indices = list(range(min(ENV_CHANNELS, stack.shape[0])))
            src = stack[indices]

            dst = np.zeros((ENV_CHANNELS, H, W), dtype=np.float32)
            src_bounds = data.get("bounds", (-3.0, 4.0, 2.0, 12.0))
            src_transform = rasterio.transform.from_bounds(*src_bounds, width=src.shape[2], height=src.shape[1])
            for i in range(ENV_CHANNELS):
                reproject(
                    source=src[i],
                    destination=dst[i],
                    src_transform=src_transform,
                    src_crs=src_crs,
                    dst_transform=dst_transform,
                    dst_crs=aoi.crs,
                    resampling=Resampling.bilinear,
                )
            return dst
        except Exception:
            pass

    # 5. Default fallback: zeros
    return np.zeros((ENV_CHANNELS, H, W), dtype=np.float32)
