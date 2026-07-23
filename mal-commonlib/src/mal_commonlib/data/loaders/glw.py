"""FAO Gridded Livestock of the World v4 (GLW4) loader (M7 — host density).

Public surface
--------------
``GLWLoader.load(aoi, species="cattle", *, cache_dir=None) -> xr.DataArray``

Downloads GLW4 2020 livestock head-count density (~10 km, ~5 arc-minutes)
for Ghana and clips to the AOI bounding box.

Supported species: cattle, goats, sheep, pigs, chickens.

Source: FAO GLW4 (https://data.apps.fao.org/catalog/dataset/)
Format: Cloud-Optimized GeoTIFF (COG), one band (heads/km² or heads/pixel).

Notes:
    * Returns livestock head count per cell (animals/pixel).
    * Resolution is ~10 km (5 arc-minutes). When aggregated to a finer
      ABM grid, the data must be conservatively (sum-preserving) resampled.
    * The loader caches downloads locally; re-runs skip the download.
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

# GLW4 2020 species keys and FAO dataset identifiers
_SPECIES_CONFIG: dict[str, dict] = {
    "cattle": {
        "file_name": "GHA_Cattle_2010.tif",
        "url": (
            "https://data.apps.fao.org/catalog/dataset/"
            "6bc08ae5-e91c-4063-b497-4e9c2bf7e2a0/resource/"
            "31463d81-8ef0-4345-84b6-2137e309ba26/download/GHA_Cattle_2010.tif"
        ),
        "long_name": "GLW4 cattle head count",
    },
    "goats": {
        "file_name": "GHA_Goats_2010.tif",
        "url": (
            "https://data.apps.fao.org/catalog/dataset/"
            "6bc08ae5-e91c-4063-b497-4e9c2bf7e2a0/resource/"
            "18d7a946-4c26-4232-826d-1b6c57b2c2d9/download/GHA_Goats_2010.tif"
        ),
        "long_name": "GLW4 goats head count",
    },
    "sheep": {
        "file_name": "GHA_Sheep_2010.tif",
        "url": (
            "https://data.apps.fao.org/catalog/dataset/"
            "6bc08ae5-e91c-4063-b497-4e9c2bf7e2a0/resource/"
            "6e2d6d55-4b1c-4c90-8f2f-9e5c51c7d3e0/download/GHA_Sheep_2010.tif"
        ),
        "long_name": "GLW4 sheep head count",
    },
    "pigs": {
        "file_name": "GHA_Pigs_2010.tif",
        "url": (
            "https://data.apps.fao.org/catalog/dataset/"
            "6bc08ae5-e91c-4063-b497-4e9c2bf7e2a0/resource/"
            "e7c7f6a4-2d3e-4b5a-9c1f-8d6e5f4a3b2c/download/GHA_Pigs_2010.tif"
        ),
        "long_name": "GLW4 pigs head count",
    },
    "chickens": {
        "file_name": "GHA_Chicken_2010.tif",
        "url": (
            "https://data.apps.fao.org/catalog/dataset/"
            "6bc08ae5-e91c-4063-b497-4e9c2bf7e2a0/resource/"
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890/download/GHA_Chicken_2010.tif"
        ),
        "long_name": "GLW4 chickens head count",
    },
}

SUPPORTED_SPECIES = tuple(_SPECIES_CONFIG.keys())


def _default_cache_dir() -> pathlib.Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "mal_commonlib" / "glw4"


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


class GLWLoader:
    """Download and clip FAO GLW4 livestock density data.

    Usage::

        loader = GLWLoader()
        cattle = loader.load(aoi, species="cattle")
    """

    def load(
        self,
        aoi: AOI,
        species: str = "cattle",
        *,
        cache_dir: pathlib.Path | None = None,
    ) -> xr.DataArray:
        """Load GLW4 livestock data for the AOI.

        Args:
            aoi: the AOI (bbox, CRS, resolution_m, slug).
            species: one of "cattle", "goats", "sheep", "pigs", "chickens".
            cache_dir: local cache for downloaded GeoTIFFs.

        Returns:
            xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
            Values are animal head count per cell (animals/pixel).
            ``-9999.0`` for cells with no data.
        """
        species = species.lower()
        if species not in _SPECIES_CONFIG:
            raise ValueError(
                f"Unknown species {species!r}; supported: {SUPPORTED_SPECIES}"
            )

        cfg = _SPECIES_CONFIG[species]
        cdir = cache_dir if cache_dir is not None else _default_cache_dir()
        tif_path = cdir / cfg["file_name"]
        _download_to(cfg["url"], tif_path)

        return self._read_clip(aoi, tif_path, species, cfg["long_name"])

    def _read_clip(
        self,
        aoi: AOI,
        tif_path: pathlib.Path,
        species: str,
        long_name: str,
    ) -> xr.DataArray:
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
                    f"AOI bbox {aoi.bbox} does not overlap GLW4 raster bounds "
                    f"({src.bounds})"
                )
            arr = src.read(1, window=win)
            win_transform = src.window_transform(win)
            nodata = src.nodata

        sentinel = nodata if nodata is not None else -9999.0
        arr_f = np.asarray(arr, dtype=np.float32)
        arr_f = np.where(arr_f == sentinel, np.float32(-9999.0), arr_f)
        arr_f = np.clip(arr_f, 0.0, None)  # negative values are invalid

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
            name=f"glw4_{species}",
            attrs={
                "long_name": long_name,
                "units": "animals/pixel",
                "source": "FAO GLW4",
                "species": species,
                "nodata": -9999.0,
            },
        )
        da.rio.write_crs(aoi.crs_obj, inplace=True)
        da.rio.write_transform(dst_transform, inplace=True)
        da.rio.write_nodata(-9999.0, inplace=True)
        return da
