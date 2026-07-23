"""GHS-SMOD Settlement Classification loader (M7 — host density).

Public surface
--------------
``GHSLLoader.load(aoi, *, cache_dir=None) -> xr.DataArray``

Downloads the GHS-SMOD 2025 settlement classification (250 m) and clips
it to the AOI bounding box. Classes: 20 (water), 30 (urban), 50 (rural).

Source: GHSL — Global Human Settlement Layer
(https://ghsl.jrc.ec.europa.eu/download.php)
Product: GHS_SMOD_E2025_GMAP_250 (250 m, 2025 epoch)

Notes:
    * Returns integer class codes: 30 (urban), 50 (rural), 20 (water/no data).
    * Resampling for categorical data MUST be nearest-neighbor.
    * The loader caches the downloaded raster locally.
"""
from __future__ import annotations

import os
import pathlib
import shutil
from typing import TYPE_CHECKING

import numpy as np
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

if TYPE_CHECKING:
    from mal_commonlib.aoi import AOI

# GHS-SMOD 2025 — Ghana tile
# The GHSL distributes GHS-SMOD as per-continent tiles.
# For Ghana (West Africa), the tile is Africa (AF).
_GHSL_URL = (
    "https://ghsl.jrc.ec.europa.eu/download/GHS_SMOD_E2025_GMAP_250/v2/"
    "GHS_SMOD_E2025_GMAP_250_AF.tif"
)
_GHSL_FILE_NAME = "GHS_SMOD_E2025_GMAP_250_AF.tif"

# GHS-SMOD class codes
GHSL_URBAN = 30
GHSL_RURAL = 50
GHSL_WATER = 20


def _default_cache_dir() -> pathlib.Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "mal_commonlib" / "ghsl"


def _download_to(url: str, dest: pathlib.Path, *, timeout: int = 120) -> pathlib.Path:
    """Stream ``url`` to ``dest`` (skip if already cached)."""
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    with requests.get(url, stream=True, timeout=timeout, allow_redirects=True) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
        shutil.move(str(tmp), str(dest))
    return dest


def _aoi_to_src_bbox(aoi: AOI) -> tuple[float, float, float, float]:
    """Transform AOI bbox to WGS-84 for windowed reads."""
    import pyproj

    if str(aoi.crs_obj).upper() in {"EPSG:4326", "WGS84", "4326"}:
        return aoi.bbox
    t = pyproj.Transformer.from_crs(aoi.crs, "EPSG:4326", always_xy=True)
    w, s, e, n = aoi.bbox
    w, s = t.transform(w, s)
    e, n = t.transform(e, n)
    return (float(w), float(s), float(e), float(n))


class GHSLLoader:
    """Download and clip GHS-SMOD settlement classification data.

    Usage::

        loader = GHSLLoader()
        smod = loader.load(aoi)
    """

    def load(
        self,
        aoi: AOI,
        *,
        cache_dir: pathlib.Path | None = None,
    ) -> xr.DataArray:
        """Load GHS-SMOD settlement classification for the AOI.

        Args:
            aoi: the AOI (bbox, CRS, resolution_m, slug).
            cache_dir: local cache for the downloaded raster.

        Returns:
            xr.DataArray with dims (y, x), dtype int32, CRS = aoi.crs.
            Values are integer class codes: 30 (urban), 50 (rural), 20 (water).
        """
        cdir = cache_dir if cache_dir is not None else _default_cache_dir()
        tif_path = cdir / _GHSL_FILE_NAME
        _download_to(_GHSL_URL, tif_path)

        return self._read_clip(aoi, tif_path)

    def _read_clip(self, aoi: AOI, tif_path: pathlib.Path) -> xr.DataArray:
        """Read the cached GeoTIFF and clip to the AOI bbox."""
        import rasterio.windows

        bbox_wgs84 = _aoi_to_src_bbox(aoi)
        w, s, e, n = bbox_wgs84

        with rasterio.open(str(tif_path)) as src:
            src_crs = src.crs
            if not str(aoi.crs_obj).upper() in {"EPSG:4326", "WGS84", "4326"}:
                import pyproj

                t = pyproj.Transformer.from_crs(aoi.crs, src_crs, always_xy=True)
                w_t, s_t = t.transform(w, s)
                e_t, n_t = t.transform(e, n)
                win = rasterio.windows.from_bounds(w_t, s_t, e_t, n_t, src.transform)
            else:
                win = rasterio.windows.from_bounds(w, s, e, n, src.transform)

            win = win.intersection(
                rasterio.windows.Window(0, 0, src.width, src.height)
            )
            if win.width <= 0 or win.height <= 0:
                raise ValueError(
                    f"AOI bbox {aoi.bbox} does not overlap GHSL raster bounds "
                    f"({src.bounds})"
                )
            arr = src.read(1, window=win)
            win_transform = src.window_transform(win)
            nodata = src.nodata

        sentinel = nodata if nodata is not None else -9999.0
        arr_i = np.asarray(arr, dtype=np.int32)
        # Map nodata to a sentinel value
        if nodata is not None:
            arr_i = np.where(arr == nodata, -9999, arr_i)

        h, w_cells = aoi.cells_per_side()
        dst_transform = from_bounds(*aoi.bbox, w_cells, h)
        out_f = np.full((h, w_cells), -9999.0, dtype=np.float32)

        from rasterio.warp import reproject

        reproject(
            source=arr_i.astype(np.float32),
            destination=out_f,
            src_transform=win_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=aoi.crs_obj,
            resampling=Resampling.nearest,
        )
        out = out_f.astype(np.int32)

        da = xr.DataArray(
            out,
            dims=("y", "x"),
            name="ghsl_smod",
            attrs={
                "long_name": "GHS-SMOD settlement classification",
                "units": "class code (30=urban, 50=rural, 20=water)",
                "source": "GHS-SMOD E2025 250m",
                "nodata": -9999,
                "urban_class": GHSL_URBAN,
                "rural_class": GHSL_RURAL,
            },
        )
        da.rio.write_crs(aoi.crs_obj, inplace=True)
        da.rio.write_transform(dst_transform, inplace=True)
        da.rio.write_nodata(-9999, inplace=True)
        return da
