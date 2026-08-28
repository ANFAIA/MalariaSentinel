"""Overture Maps Buildings loader (M7 — host density).

Public surface
--------------
``load_buildings_fraction(aoi, *, cache_dir=None) -> xr.DataArray``

Downloads Overture Maps building footprints for the AOI and rasterizes
them to a building-fraction layer (fraction of each ABM cell covered by
building footprints).

Source: Overture Maps Foundation (https://overturemaps.org/)
Format: GeoParquet hosted on S3 (``s3://overturemaps-us-west-2``), one row
per building footprint.

Implementation notes:
    * Downloads go through DuckDB (httpfs + spatial): the S3 parquet dataset
      is read with bbox predicate pushdown (row-group pruning via the ``bbox``
      struct column) and rasterized inside SQL (footprint centroid -> cell
      index). Python never materialises the full footprint set (Ghana alone
      is ~17M footprints).
    * The Overture layout is release-based (``release/YYYY-MM-DD.N``); the
      newest release is resolved by listing the S3 bucket.
    * The resulting raster is cached as ``.npz`` keyed by AOI + release;
      re-runs skip the download entirely.
    * Values are in [0, 1] (1.0 = at least one footprint centroid in cell).
    * NoData value is -9999.0 (cells with no buildings).
"""
from __future__ import annotations

import os
import pathlib
import warnings
from typing import TYPE_CHECKING

import numpy as np
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.transform import from_bounds

if TYPE_CHECKING:
    from mal_commonlib.aoi import AOI


__all__ = ["load_buildings_fraction", "BuildingsLoader", "DOWNLOADER"]

_OVERTURE_S3_BUCKET = "overturemaps-us-west-2"
_OVERTURE_S3_REGION = "us-west-2"
_NODATA = -9999.0


def _default_cache_dir() -> pathlib.Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return pathlib.Path(base) / "mal_commonlib" / "buildings"


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


def _resolve_latest_release() -> str:
    """List Overture S3 releases and return the newest (YYYY-MM-DD.N)."""
    import pyarrow.fs as fs

    s3 = fs.S3FileSystem(anonymous=True, region=_OVERTURE_S3_REGION)
    selector = fs.FileSelector(f"{_OVERTURE_S3_BUCKET}/release", recursive=False)
    versions = [
        info.path.rsplit("/", 1)[-1]
        for info in s3.get_file_info(selector)
        if info.path.rsplit("/", 1)[-1][0].isdigit()
    ]
    if not versions:
        raise RuntimeError("No Overture releases found in S3 bucket")
    return max(versions)  # 'YYYY-MM-DD.N' sorts lexically


def _aoi_crs_epsg(aoi: AOI) -> int:
    epsg = aoi.crs_obj.to_epsg()
    if epsg is None:
        raise ValueError(f"AOI CRS has no EPSG code: {aoi.crs}")
    return epsg


def _cell_size(aoi: AOI) -> tuple[float, float]:
    """Cell size in AOI CRS units (meters for projected, degrees for 4326)."""
    if _aoi_crs_epsg(aoi) == 4326:
        h, w_cells = aoi.cells_per_side()
        w_deg, s_deg, e_deg, n_deg = aoi.bbox
        return ((e_deg - w_deg) / w_cells, (n_deg - s_deg) / h)
    return (float(aoi.resolution_m), float(aoi.resolution_m))


def _download_and_rasterize(
    bbox_wgs84: tuple[float, float, float, float],
    aoi: AOI,
    cache_dir: pathlib.Path,
) -> np.ndarray:
    """Download Overture buildings and rasterize to the AOI grid via DuckDB."""
    import duckdb

    release = _resolve_latest_release()
    parquet_glob = (
        f"s3://{_OVERTURE_S3_BUCKET}/release/{release}/"
        f"theme=buildings/type=building/*.zstd.parquet"
    )
    w, s, e, n = bbox_wgs84
    w0, s0, e0, n0 = aoi.bbox
    cell_w, cell_h = _cell_size(aoi)
    nrows, ncols = aoi.cells_per_side()
    epsg = _aoi_crs_epsg(aoi)
    target_crs = f"EPSG:{epsg}"

    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute("INSTALL spatial; LOAD spatial;")
        con.execute(f"SET s3_region='{_OVERTURE_S3_REGION}';")
        rows = con.execute(
            """
            SELECT DISTINCT cx, cy FROM (
                SELECT
                    CAST(floor((ST_X(pt) - $w0) / $cell_w) AS BIGINT) AS cx,
                    CAST(floor(($n0 - ST_Y(pt)) / $cell_h) AS BIGINT) AS cy
                FROM (
                    SELECT ST_Transform(
                        ST_Centroid(geometry),
                        'EPSG:4326', $target_crs
                    ) AS pt
                    FROM read_parquet($parquet_glob)
                    WHERE bbox.xmin <= $e AND bbox.xmax >= $w
                      AND bbox.ymin <= $n AND bbox.ymax >= $s
                      AND geometry IS NOT NULL
                )
            )
            WHERE cx >= 0 AND cx < $ncols AND cy >= 0 AND cy < $nrows
            """,
            {
                "parquet_glob": parquet_glob,
                "w": w, "s": s, "e": e, "n": n,
                "w0": w0, "n0": n0,
                "cell_w": cell_w, "cell_h": cell_h,
                "target_crs": target_crs,
                "ncols": ncols, "nrows": nrows,
            },
        ).fetchall()
    finally:
        con.close()

    fraction = np.full((nrows, ncols), _NODATA, dtype=np.float32)
    for cx, cy in rows:
        fraction[cy, cx] = 1.0

    cache_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cache_dir / f"buildings_{aoi.slug}_{release}.npz", fraction=fraction
    )
    return fraction


def load_buildings_fraction(
    aoi: AOI | str,
    *,
    cache_dir: pathlib.Path | None = None,
) -> xr.DataArray:
    """Load building footprint fraction for the AOI.

    Args:
        aoi: the AOI (bbox, CRS, resolution_m, slug) or string slug.
        cache_dir: local cache for downloaded data.

    Returns:
        xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
        Values in [0, 1] (1.0 = building centroid present in cell).
        ``-9999.0`` for cells with no data.
    """
    if isinstance(aoi, str):
        from mal_commonlib.aoi import AOI
        aoi = AOI.from_slug(aoi)

    cdir = pathlib.Path(cache_dir) if cache_dir is not None else _default_cache_dir()

    # Cached raster for this AOI + latest release?
    release = _resolve_latest_release()
    cache_path = cdir / f"buildings_{aoi.slug}_{release}.npz"
    if cache_path.exists():
        with np.load(cache_path) as z:
            fraction = z["fraction"].astype(np.float32, copy=False)
    else:
        bbox_wgs84 = _aoi_to_src_bbox(aoi)
        fraction = _download_and_rasterize(bbox_wgs84, aoi, cdir)

    da = xr.DataArray(
        fraction,
        dims=("y", "x"),
        name="building_fraction",
        attrs={
            "long_name": "Building footprint fraction",
            "units": "fraction [0, 1]",
            "source": "Overture Maps Foundation",
            "overture_release": release,
            "nodata": _NODATA,
        },
    )
    da.rio.write_crs(aoi.crs_obj, inplace=True)
    da.rio.write_transform(from_bounds(*aoi.bbox, *aoi.cells_per_side()[::-1]), inplace=True)
    da.rio.write_nodata(_NODATA, inplace=True)
    return da


class BuildingsLoader:
    """DEPRECATED: Use load_buildings_fraction() instead."""

    def load(
        self,
        aoi: AOI,
        *,
        cache_dir: pathlib.Path | None = None,
    ) -> xr.DataArray:
        warnings.warn(
            "BuildingsLoader is deprecated; use load_buildings_fraction()",
            DeprecationWarning,
            stacklevel=2,
        )
        return load_buildings_fraction(aoi, cache_dir=cache_dir)


DOWNLOADER = {
    "name": "buildings",
    "description": "Overture Maps building footprint fraction",
    "requires_auth": ["none"],
    "is_time_series": False,
    "outputs": {
        "building_fraction": load_buildings_fraction,
    },
    "manifest_keys": {
        "building_fraction": "buildings",
    },
}
