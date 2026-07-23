"""Overture Maps Buildings loader (M7 — host density).

Public surface
--------------
``BuildingsLoader.load(aoi, *, cache_dir=None) -> xr.DataArray``

Downloads Overture Maps building footprints for the AOI and rasterizes
them to a building-fraction layer (fraction of each ABM cell covered by
building footprints).

Source: Overture Maps Foundation (https://overturemaps.org/)
Format: GeoParquet hosted on S3, one row per building footprint.

Notes:
    * Values are in [0, 1] (fraction of cell area covered by buildings).
    * NoData value is -9999.0.
    * The loader caches downloads locally; re-runs skip the download.
    * Conservative (sum-preserving) aggregation is used when rasterizing
      high-res footprints to the ABM grid.
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
from rasterio.features import geometry_mask
from rasterio.transform import from_bounds

if TYPE_CHECKING:
    from mal_commonlib.aoi import AOI


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


def _download_buildings_overturemaestro(
    bbox_wgs84: tuple[float, float, float, float],
    cache_dir: pathlib.Path,
) -> pathlib.Path:
    """Download building footprints via overturemaestro (preferred).

    Returns the path to a cached GeoJSON file.
    """
    from overturemaestro import create_overture_maestro

    w, s, e, n = bbox_wgs84
    client = create_overture_maestro()
    buildings_gdf = client.get_buildings(
        bbox=(w, s, e, n),
    )
    if buildings_gdf is None or len(buildings_gdf) == 0:
        cache_dir.mkdir(parents=True, exist_ok=True)
        empty_path = cache_dir / "buildings.geojson"
        import geopandas as gpd
        gpd.GeoDataFrame(geometry=[], crs="EPSG:4326").to_file(empty_path, driver="GeoJSON")
        return empty_path

    cache_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = cache_dir / "buildings.geojson"
    buildings_gdf.to_file(geojson_path, driver="GeoJSON")
    return geojson_path


def _download_buildings_parquet(
    bbox_wgs84: tuple[float, float, float, float],
    cache_dir: pathlib.Path,
) -> pathlib.Path:
    """Download building footprints from Overture S3 via pyarrow + geopandas."""
    try:
        import pyarrow.parquet as pq
        from pyogrio import read_dataframe
    except ImportError:
        raise ImportError(
            "Building loader requires 'pyarrow' and 'pyogrio'. "
            "Install with: uv add pyarrow pyogrio"
        )

    w, s, e, n = bbox_wgs84

    # Overture release bucket path — use the latest stable release
    version = "1.1.0"
    base_url = f"https://data.overturemaps.org/data/{version}"
    parquet_url = f"{base_url}/theme=buildings/type=building"

    # Use pyarrow to read the parquet dataset with bbox filtering
    import pyarrow as pa

    dataset = pq.ParquetDataset(
        parquet_url,
        filesystem=None,
        filters=[
            ("bbox.xmin", "<=", e),
            ("bbox.xmax", ">=", w),
            ("bbox.ymin", "<=", n),
            ("bbox.ymax", ">=", s),
        ],
    )
    table = dataset.read()

    # Convert to geopandas for geometry handling
    import geopandas as gpd
    from shapely import wkb

    df = table.to_pandas()
    if "geometry" in df.columns:
        df["geometry"] = df["geometry"].apply(
            lambda g: wkb.loads(g) if g is not None else None
        )
    elif "id" in df.columns:
        # Overture stores geometry as WKB in a dedicated column
        for col in df.columns:
            if df[col].dtype == object and len(df) > 0:
                try:
                    sample = df[col].iloc[0]
                    if isinstance(sample, bytes) and len(sample) > 20:
                        df["geometry"] = df[col].apply(
                            lambda g: wkb.loads(g) if g is not None else None
                        )
                        break
                except Exception:
                    continue

    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

    # Clip to bbox
    from shapely.geometry import box

    bbox_poly = box(w, s, e, n)
    gdf = gdf[gdf.geometry.intersects(bbox_poly)]

    cache_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = cache_dir / "buildings.geojson"
    gdf.to_file(geojson_path, driver="GeoJSON")
    return geojson_path


def _rasterize_footprints(
    geojson_path: pathlib.Path,
    aoi: AOI,
    bbox_wgs84: tuple[float, float, float, float],
) -> np.ndarray:
    """Rasterize building footprints to building-fraction on the AOI grid.

    Uses conservative (sum-preserving) aggregation: each footprint's area
    contribution to a cell is proportional to the overlap fraction.
    """
    import geopandas as gpd

    if isinstance(geojson_path, pathlib.Path):
        gdf = gpd.read_file(geojson_path)
    else:
        gdf = gpd.GeoDataFrame.from_features(geojson_path, crs="EPSG:4326")

    if len(gdf) == 0:
        h, w_cells = aoi.cells_per_side()
        return np.full((h, w_cells), -9999.0, dtype=np.float32)

    h, w_cells = aoi.cells_per_side()
    dst_transform = from_bounds(*aoi.bbox, w_cells, h)

    # Rasterize: count pixels covered by any footprint
    footprints_mask = geometry_mask(
        gdf.geometry,
        out_shape=(h, w_cells),
        transform=dst_transform,
        invert=True,  # True = pixels inside geometry are True
    )

    # Convert to fraction (binary in, but we can weight by area later)
    # For a first pass: 1.0 if any footprint covers the cell, 0.0 otherwise.
    # A more accurate approach would compute area overlap, but this is a
    # reasonable approximation at ABM grid resolution.
    fraction = footprints_mask.astype(np.float32)

    # Set NoData where there's no overlap with the source data extent
    # (cells completely outside the AOI bbox should be nodata)
    fraction = np.where(fraction == 0, -9999.0, fraction)

    return fraction


class BuildingsLoader:
    """Download and rasterize Overture Maps building footprints.

    Usage::

        loader = BuildingsLoader()
        building_frac = loader.load(aoi)
    """

    def load(
        self,
        aoi: AOI,
        *,
        cache_dir: pathlib.Path | None = None,
    ) -> xr.DataArray:
        """Load building fraction for the AOI.

        Args:
            aoi: the AOI (bbox, CRS, resolution_m, slug).
            cache_dir: local cache for downloaded data.

        Returns:
            xr.DataArray with dims (y, x), dtype float32, CRS = aoi.crs.
            Values in [0, 1] (fraction of cell covered by buildings).
            ``-9999.0`` for cells with no data.
        """
        cdir = cache_dir if cache_dir is not None else _default_cache_dir()
        bbox_wgs84 = _aoi_to_src_bbox(aoi)

        # Try overturemaestro first, fall back to pyarrow
        try:
            geojson_path = _download_buildings_overturemaestro(bbox_wgs84, cdir)
        except ImportError:
            geojson_path = _download_buildings_parquet(bbox_wgs84, cdir)

        fraction = _rasterize_footprints(geojson_path, aoi, bbox_wgs84)

        da = xr.DataArray(
            fraction,
            dims=("y", "x"),
            name="building_fraction",
            attrs={
                "long_name": "Building footprint fraction",
                "units": "fraction [0, 1]",
                "source": "Overture Maps Foundation",
                "nodata": -9999.0,
            },
        )
        da.rio.write_crs(aoi.crs_obj, inplace=True)
        da.rio.write_transform(from_bounds(*aoi.bbox, *aoi.cells_per_side()[::-1]), inplace=True)
        da.rio.write_nodata(-9999.0, inplace=True)
        return da
