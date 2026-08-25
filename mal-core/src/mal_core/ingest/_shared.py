"""Shared helpers for the ingest stage."""
from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any, Callable

import numpy as np
import requests
import xarray as xr

from mal_commonlib.aoi import AOI, Scale

log = logging.getLogger(__name__)

NODATA_SENTINEL: float = -9999.0


def resolve_aoi(
    aoi: str | None,
    bbox: str | None,
    crs: str,
    resolution_m: int,
    scale: Scale,
    name: str | None,
) -> AOI:
    """Build an AOI from either the YAML slug registry or an explicit bbox."""
    if bbox is not None:
        parts = [p.strip() for p in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError(f"bbox must be 4 floats 'W,S,E,N'; got {bbox!r}")
        w, s, e, n = (float(x) for x in parts)
        slug = aoi if aoi else "custom"
        return AOI.from_bbox(
            west=w, south=s, east=e, north=n,
            crs=crs, slug=slug, resolution_m=resolution_m,
            name=name, scale=scale,
        )
    if aoi is None:
        raise ValueError("either aoi or bbox is required")
    return AOI.from_slug(aoi)


def safe_load(
    loader_fn: Callable[..., Any],
    aoi: AOI,
    channel_name: str,
    year: int | None = None,
    month: int | None = None,
    *,
    default_value: float = NODATA_SENTINEL,
    **kwargs,
) -> Any:
    """Call a loader; on auth/network failure, return a NoData-filled channel."""
    try:
        sig = inspect.signature(loader_fn)
        accepted = set(sig.parameters.keys())
        call_kwargs: dict[str, Any] = {"aoi": aoi}

        if "years" in accepted and year is not None:
            call_kwargs["years"] = [year]
        elif "year" in accepted and year is not None:
            call_kwargs["year"] = year

        if "months" in accepted and month is not None:
            call_kwargs["months"] = [month]
        elif "month" in accepted and month is not None:
            call_kwargs["month"] = month

        if "cache_dir" in accepted:
            call_kwargs["cache_dir"] = kwargs.get("cache_dir")
        return loader_fn(**call_kwargs)
    except (RuntimeError, FileNotFoundError, OSError, requests.RequestException) as exc:
        log.warning(
            "%s loader failed: %r. Filling with NoData (%s).",
            channel_name, exc, default_value,
        )
        return empty_channel(aoi, value=default_value, band_name=channel_name)


def empty_channel(aoi: AOI, *, value: float, band_name: str) -> xr.DataArray:
    """Return a (y, x) DataArray on the AOI's grid filled with ``value``."""
    from rasterio.transform import from_bounds
    import rioxarray  # noqa: F401

    h, w = aoi.cells_per_side()
    arr = np.full((h, w), float(value), dtype=np.float32)
    transform = from_bounds(*aoi.bbox, w, h)
    da = xr.DataArray(
        arr,
        dims=("y", "x"),
        name=band_name,
        attrs={
            "long_name": f"{band_name} (NoData fill)",
            "band_name": band_name,
            "aoi_slug": aoi.slug,
            "nodata": NODATA_SENTINEL,
            "fill": True,
        },
    )
    da.rio.write_crs(aoi.crs_obj, inplace=True)
    da.rio.write_transform(transform, inplace=True)
    da.rio.write_nodata(NODATA_SENTINEL, inplace=True)
    return da


def register_dataset(
    aoi_slug: str,
    dataset_name: str,
    year: int | str | None,
    filename: str,
    *,
    type: str = "static",
    required_for_abm: bool = False,
    variables: list[str] | None = None,
    format: str | None = None,
    data_root: Path | None = None,
) -> None:
    """Register a build output in the central manifest."""
    import json

    from mal_core.download.manifest import read_manifest, update_dataset

    update_dataset(aoi_slug, dataset_name, year, filename, type=type, required_for_abm=required_for_abm, variables=variables, format=format, data_root=data_root)

    manifest = read_manifest(aoi_slug)
    ds = manifest.get("datasets", {}).get(dataset_name, {})
    if required_for_abm:
        ds["required_for_abm"] = True
    if variables:
        ds["variables"] = variables
    if format:
        ds["format"] = format

    manifest_path = Path("data") / aoi_slug / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
