"""Download runner — orchestrates downloads for an AOI via the plugin registry."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import xarray as xr

from .registry import DownloaderSpec, discover_downloaders
from .manifest import update_dataset, validate_completeness
from .writer import save_product

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _check_auth(spec: DownloaderSpec) -> bool:
    for auth in spec.requires_auth:
        if auth == "cds":
            cdsapirc = Path.home() / ".cdsapirc"
            if not cdsapirc.exists():
                log.warning("Downloader '%s' requires CDS auth (~/.cdsapirc) — skipping", spec.name)
                return False
        elif auth == "earthdata":
            import os
            if not os.environ.get("EARTHDATA_TOKEN"):
                log.warning("Downloader '%s' requires EARTHDATA_TOKEN — skipping", spec.name)
                return False
    return True


def _standard_path(aoi: str, product: str, year: int | None, ext: str, data_dir: Path | None = None) -> Path:
    data_dir = data_dir or (_REPO_ROOT / "data" / aoi)
    if year:
        return data_dir / f"{aoi}_{product}_{year}.{ext}"
    return data_dir / f"{aoi}_{product}.{ext}"


def _standard_path_daily(aoi: str, product: str, year_start: int, year_end: int, data_dir: Path | None = None) -> Path:
    """Path for multi-year daily NC output: data/<aoi>/<aoi>_<product>_<start>_<end>_daily.nc"""
    data_dir = data_dir or (_REPO_ROOT / "data" / aoi)
    return data_dir / f"{aoi}_{product}_{year_start}_{year_end}_daily.nc"



def run_download(
    aoi: str,
    datasets: list[str] | None = None,
    outputs: list[str] | None = None,
    years: list[int] | None = None,
    months: list[int] | None = None,
    output_dir: str | Path | None = None,
    cache_dir: str | Path | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Download datasets for an AOI, using standard naming + manifest registration."""
    from mal_commonlib.aoi import AOI

    aoi_obj = AOI.from_slug(aoi)
    registry = discover_downloaders()
    if not registry:
        return {"error": "No downloaders registered"}

    if datasets:
        selected = {k: v for k, v in registry.items() if k in datasets}
    else:
        selected = registry

    out_dir = Path(output_dir) if output_dir else (_REPO_ROOT / "data" / aoi)
    out_dir.mkdir(parents=True, exist_ok=True)

    cache = Path(cache_dir) if cache_dir else None

    results: dict[str, Any] = {}
    use_abm_profile = datasets is None and outputs is None
    for name, spec in selected.items():
        log.info("Downloading: %s", name)
        if not _check_auth(spec):
            results[name] = {"status": "skipped", "reason": "auth missing"}
            continue

        try:
            for output_name, func in spec.outputs.items():
                if outputs and output_name not in outputs:
                    continue
                if use_abm_profile and spec.abm_default_outputs is not None and output_name not in spec.abm_default_outputs:
                    continue

                log.info("  %s.%s", name, output_name)
                is_ts = spec.is_time_series
                required_for_abm = bool(spec.required_for_abm and spec.required_for_abm.get(output_name, False))

                if is_ts:
                    if not years:
                        log.warning("    %s is time-series but no years specified — skipping", output_name)
                        continue

                    # Determine format for this output (default: "monthly" for backward compat)
                    output_format = "monthly"
                    if spec.formats and output_name in spec.formats:
                        output_format = spec.formats[output_name]

                    if output_format == "daily":
                        # Daily path: write entire 3D time-series as ONE multi-year NC
                        result = func(aoi=aoi_obj, years=years, months=months, cache_dir=cache)
                        if result is None:
                            continue
                        # 3D DataArray → NC via xarray.to_netcdf()
                        # Variable name: strip "_daily" suffix for ABM compatibility
                        # (e.g. "rainfall_daily" → "rainfall")
                        nc_var_name = output_name.removesuffix("_daily")
                        path = _standard_path_daily(aoi, output_name, min(years), max(years), data_dir=out_dir)
                        path.parent.mkdir(parents=True, exist_ok=True)
                        save_product(result, path, format="nc", var_name=nc_var_name)
                        # Register with period metadata
                        time_dim = "time" if "time" in result.dims else "valid_time"
                        t0 = str(result[time_dim].values[0])[:10]
                        t1 = str(result[time_dim].values[-1])[:10]
                        update_dataset(
                            aoi,
                            spec.manifest_keys[output_name],
                            None,  # year=None for multi-year NC
                            path.name,
                            type="time-series",
                            required_for_abm=required_for_abm,
                            format="nc",
                            period={"start": t0, "end": t1},
                            data_root=out_dir.parent,
                        )
                        log.info("    daily NC → %s (period %s to %s)", path.name, t0, t1)
                    else:
                        # Monthly path: existing M11 logic (per-month TIF slicing)
                        result = func(aoi=aoi_obj, years=years, months=months, cache_dir=cache)
                        if result is None:
                            continue

                        has_time = "time" in result.dims or "valid_time" in result.dims
                        if has_time:
                            time_dim = "valid_time" if "valid_time" in result.dims else "time"
                            for yr in years:
                                sel = result.sel({time_dim: result[time_dim].dt.year == yr})
                                reduction = (spec.reductions or {}).get(output_name, "mean")
                                if reduction == "sum":
                                    slc = sel.sum(time_dim, keep_attrs=True)
                                elif reduction == "first":
                                    slc = sel.isel({time_dim: 0}, drop=True)
                                else:
                                    slc = sel.mean(time_dim, keep_attrs=True)
                                path = _standard_path(aoi, output_name, yr, "tif", data_dir=out_dir)
                                save_product(slc, path, format="tif")
                                update_dataset(
                                    aoi,
                                    spec.manifest_keys[output_name],
                                    yr,
                                    path.name,
                                    type="time-series",
                                    required_for_abm=required_for_abm,
                                    format="tif",
                                    data_root=out_dir.parent,
                                )
                                log.info("    %s aggregate (%s) → %s", yr, reduction, path.name)
                        else:
                            # Single (year, month) — 2D result, no time dim
                            yr = years[0]
                            path = _standard_path(aoi, output_name, yr, "tif", data_dir=out_dir)
                            save_product(result, path, format="tif")
                            update_dataset(
                                aoi,
                                spec.manifest_keys[output_name],
                                yr,
                                path.name,
                                type="time-series",
                                required_for_abm=required_for_abm,
                                format="tif",
                                data_root=out_dir.parent,
                            )
                            log.info("    %s → %s", yr, path.name)
                else:
                    result = func(aoi=aoi_obj, cache_dir=cache)

                    if result is None:
                        continue

                    ext = ".nc" if isinstance(result, xr.Dataset) else ".tif"
                    path = _standard_path(aoi, output_name, None, ext.lstrip("."), data_dir=out_dir)
                    save_product(result, path)
                    update_dataset(
                        aoi,
                        spec.manifest_keys[output_name],
                        None,
                        path.name,
                        type="static",
                        required_for_abm=required_for_abm,
                        data_root=out_dir.parent,
                    )
                    log.info("    → %s", path.name)

            results[name] = {"status": "ok"}
        except Exception as e:
            log.error("Download failed for %s: %s", name, e)
            results[name] = {"status": "error", "error": str(e)}

    return results
