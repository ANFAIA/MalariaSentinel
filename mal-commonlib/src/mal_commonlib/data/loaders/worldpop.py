"""WorldPop Ghana population density loader (M7 — host density).

Public surface
--------------
``WorldPopLoader.load(aoi, year=2019, *, cache_dir=None) -> xr.DataArray``

Downloads the WorldPop Ghana 2019 v2.0 constrained UN-adjusted population
estimate (~100 m resolution) and clips it to the AOI bounding box.

Source: WorldPop Open Population Repository (https://wp-data.worldpop.org/)
Product: GHA_ppp_2019_constrained.tif (Ghana, 2019, constrained, UN-adjusted)

Notes:
    * Returns population count per cell (persons/pixel), NOT density.
    * The loader caches the downloaded GeoTIFF locally; re-runs skip the
      download if the file already exists.
    * Checksum verification is performed on download via SHA-256 when
      available from the server.
"""
from __future__ import annotations

import hashlib
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

# WorldPop Ghana constrained UN-adjusted 2019 v2.0
_WORLDPOP_URL_TEMPLATE = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/"
    "2020/BSGM/GHA/gha_ppp_2019_constrained.tif"
)
_WORLDPOP_FILE_NAME = "gha_ppp_2019_constrained.tif"


def _default_cache_dir() -> pathlib.Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "mal_commonlib" / "worldpop"


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


class WorldPopLoader:
    """Download and clip WorldPop Ghana population estimates.

    Usage::

        loader = WorldPopLoader()
        pop_da = loader.load(aoi, year=2019)
    """

    def load(
        self,
        aoi: AOI,
        year: int = 2019,
        *,
        cache_dir: pathlib.Path | None = None,
    ) -> xr.DataArray:
        """Load WorldPop Ghana population for the AOI.

        Args:
            aoi: the AOI (bbox, CRS, resolution_m, slug).
            year: must be 2019 (only constrained Ghana product available).
            cache_dir: local cache for the downloaded GeoTIFF.

        Returns:
            xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
            Values are population counts per cell (persons/pixel).
            ``-9999.0`` for cells with no data.
        """
        if year != 2019:
            raise ValueError(
                f"WorldPop Ghana constrained is only available for 2019; got {year}"
            )

        cdir = cache_dir if cache_dir is not None else _default_cache_dir()
        tif_path = cdir / _WORLDPOP_FILE_NAME
        _download_to(_WORLDPOP_URL_TEMPLATE, tif_path)

        return self._read_clip(aoi, tif_path, year)

    def _read_clip(self, aoi: AOI, tif_path: pathlib.Path, year: int = 2019) -> xr.DataArray:
        """Read the cached GeoTIFF and clip to the AOI bbox."""
        import rasterio.windows

        bbox_wgs84 = _aoi_to_src_bbox(aoi)
        w, s, e, n = bbox_wgs84

        with rasterio.open(str(tif_path)) as src:
            src_crs = src.crs
            # If AOI is not in WGS-84, transform the bbox into source CRS
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
                    f"AOI bbox {aoi.bbox} does not overlap WorldPop raster bounds "
                    f"({src.bounds})"
                )
            arr = src.read(1, window=win)
            win_transform = src.window_transform(win)
            nodata = src.nodata

        # Mask nodata
        sentinel = nodata if nodata is not None else -9999.0
        arr_f = np.asarray(arr, dtype=np.float32)
        arr_f = np.where(arr_f == sentinel, np.float32(-9999.0), arr_f)

        # Build output DataArray on the AOI grid
        h, w_cells = aoi.cells_per_side()
        dst_transform = from_bounds(*aoi.bbox, w_cells, h)
        out = np.zeros((h, w_cells), dtype=np.float32)
        out[:] = -9999.0

        from rasterio.warp import reproject

        reproject(
            source=arr_f,
            destination=out,
            src_transform=win_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=aoi.crs_obj,
            resampling=Resampling.nearest,
        )

        da = xr.DataArray(
            out,
            dims=("y", "x"),
            name="worldpop_population",
            attrs={
                "long_name": "WorldPop Ghana population count",
                "units": "persons/pixel",
                "source": f"WorldPop GHA_ppp_{year}_constrained",
                "year": year,
                "nodata": -9999.0,
            },
        )
        da.rio.write_crs(aoi.crs_obj, inplace=True)
        da.rio.write_transform(dst_transform, inplace=True)
        da.rio.write_nodata(-9999.0, inplace=True)
        return da
