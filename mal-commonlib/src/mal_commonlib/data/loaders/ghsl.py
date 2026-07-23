"""GHS-SMOD Settlement Classification loader (M7 — host density).

Public surface
--------------
``GHSLLoader.load(aoi, *, cache_dir=None) -> xr.DataArray``

Downloads the GHS-SMOD settlement classification from the JRC FTP
archive (ZIP), extracts the TIF, and clips it to the AOI bounding box.
Classes: 20 (water), 30 (urban), 50 (rural).

Source: GHSL — Global Human Settlement Layer
(https://ghsl.jrc.ec.europa.eu/download.php?ds=smod)
Product: GHS_SMOD_E2030_GLOBE_R2023A (Mollweide ~1 km, 2030 epoch)

The single-file download on the GHSL website is intermittently
unavailable.  This loader uses the stable JRC FTP mirror instead:

    https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/
      GHS_SMOD_GLOBE_R2023A/
      GHS_SMOD_E2030_GLOBE_R2023A_54009_1000/
      V2-0/
      GHS_SMOD_E2030_GLOBE_R2023A_54009_1000_V2_0.zip

The ZIP contains:
    *.tif          — the settlement classification raster
    *.clr          — colour map
    *.tif.ovr      — overview pyramids
    *.pdf          — documentation

Notes:
    * Returns integer class codes: 30 (urban), 50 (rural), 20 (water).
    * Resampling for categorical data MUST be nearest-neighbor.
    * The loader caches the extracted TIF locally; re-runs skip the
      download and extraction.
"""
from __future__ import annotations

import io
import os
import pathlib
import shutil
import zipfile
from typing import TYPE_CHECKING

import numpy as np
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

if TYPE_CHECKING:
    from mal_commonlib.aoi import AOI

# ---------------------------------------------------------------------------
# JRC FTP URL for GHS-SMOD E2030 (stable mirror, not the flaky
# ghsl.jrc.ec.europa.eu/download.php single-file endpoint).
# ---------------------------------------------------------------------------
_GHSL_ZIP_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
    "GHS_SMOD_GLOBE_R2023A/"
    "GHS_SMOD_E2030_GLOBE_R2023A_54009_1000/"
    "V2-0/"
    "GHS_SMOD_E2030_GLOBE_R2023A_54009_1000_V2_0.zip"
)
# Name of the TIF inside the ZIP (after extraction).
_GHSL_TIF_NAME = "GHS_SMOD_E2030_GLOBE_R2023A_54009_1000_V2_0.tif"
# Friendly name for the cached extracted TIF.
_GHSL_CACHE_TIF = "GHS_SMOD_E2030_R2023A_54009_1000.tif"

# GHS-SMOD class codes (R2023A scheme)
#   0, 10–19: water / no data
#   20–29:    rural (21=low, 22=medium, 23=high density)
#   30:       urban centres
GHSL_URBAN = 30
GHSL_RURAL_LOW = 21
GHSL_RURAL_MED = 22
GHSL_RURAL_HIGH = 23
GHSL_WATER = 10

# For backward compat: any class in 20–29 is rural.
GHSL_RURAL = 21  # lowest rural density; callers should use is_rural()


def _default_cache_dir() -> pathlib.Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "mal_commonlib" / "ghsl"


def _download_zip(url: str, dest: pathlib.Path, *, timeout: int = 300) -> pathlib.Path:
    """Stream a ZIP file from *url* to *dest* (skip if already cached)."""
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


def _extract_tif_from_zip(
    zip_path: pathlib.Path,
    tif_name: str,
    dest_tif: pathlib.Path,
) -> pathlib.Path:
    """Extract *tif_name* from *zip_path* into *dest_tif* (skip if exists)."""
    if dest_tif.exists() and dest_tif.stat().st_size > 0:
        return dest_tif
    dest_tif.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        # The TIF name inside the ZIP may have a directory prefix;
        # find it by suffix match.
        matches = [n for n in zf.namelist() if n.endswith(tif_name)]
        if not matches:
            raise FileNotFoundError(
                f"TIF {tif_name!r} not found in ZIP {zip_path.name}; "
                f"contents: {zf.namelist()}"
            )
        with zf.open(matches[0]) as src, open(dest_tif, "wb") as dst:
            shutil.copyfileobj(src, dst)
    return dest_tif


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

        Downloads the ZIP from JRC FTP, extracts the TIF, and clips
        to the AOI bounding box.  The source raster is in EPSG:54009
        (World Mollweide) at ~1 km; it is reprojected on-the-fly to
        the AOI's CRS via nearest-neighbour resampling (categorical data).

        Args:
            aoi: the AOI (bbox, CRS, resolution_m, slug).
            cache_dir: local cache for the downloaded/extracted raster.

        Returns:
            xr.DataArray with dims (y, x), dtype int32, CRS = aoi.crs.
            Values are integer class codes: 30 (urban), 50 (rural), 20 (water).
        """
        cdir = cache_dir if cache_dir is not None else _default_cache_dir()
        zip_path = cdir / "GHS_SMOD_E2030_R2023A_54009_1000.zip"
        tif_path = cdir / _GHSL_CACHE_TIF

        # Step 1: download ZIP (cached)
        _download_zip(_GHSL_ZIP_URL, zip_path)

        # Step 2: extract TIF from ZIP (cached)
        _extract_tif_from_zip(zip_path, _GHSL_TIF_NAME, tif_path)

        # Step 3: read, reproject, clip
        return self._read_clip(aoi, tif_path)

    def _read_clip(self, aoi: AOI, tif_path: pathlib.Path) -> xr.DataArray:
        """Read the extracted GeoTIFF, reproject, and clip to the AOI bbox."""
        import rasterio.windows
        from rasterio.warp import reproject as rio_reproject

        bbox_wgs84 = _aoi_to_src_bbox(aoi)
        w, s, e, n = bbox_wgs84

        with rasterio.open(str(tif_path)) as src:
            src_crs = src.crs
            # The source is ESRI:54009 (Mollweide).  Convert the
            # AOI's WGS-84 bbox into the source CRS for the window.
            src_crs_str = str(src_crs)
            if "54009" in src_crs_str:
                import pyproj

                t = pyproj.Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)
                w_t, s_t = t.transform(w, s)
                e_t, n_t = t.transform(e, n)
            elif str(aoi.crs_obj).upper() not in {"EPSG:4326", "WGS84", "4326"}:
                import pyproj

                t = pyproj.Transformer.from_crs(aoi.crs, src_crs, always_xy=True)
                w_t, s_t = t.transform(w, s)
                e_t, n_t = t.transform(e, n)
            else:
                w_t, s_t, e_t, n_t = w, s, e, n

            win = rasterio.windows.from_bounds(w_t, s_t, e_t, n_t, src.transform)
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
        if nodata is not None:
            arr_i = np.where(arr == nodata, -9999, arr_i)

        h, w_cells = aoi.cells_per_side()
        dst_transform = from_bounds(*aoi.bbox, w_cells, h)
        out_f = np.full((h, w_cells), -9999.0, dtype=np.float32)

        rio_reproject(
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
                "source": "GHS-SMOD E2030 R2023A (JRC FTP)",
                "nodata": -9999,
                "urban_class": GHSL_URBAN,
                "rural_class": GHSL_RURAL,
            },
        )
        da.rio.write_crs(aoi.crs_obj, inplace=True)
        da.rio.write_transform(dst_transform, inplace=True)
        da.rio.write_nodata(-9999, inplace=True)
        return da
