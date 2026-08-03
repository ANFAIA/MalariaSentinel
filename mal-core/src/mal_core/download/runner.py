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


def _standard_path(aoi: str, product: str, year: int | None, ext: str) -> Path:
    data_dir = _REPO_ROOT / "data" / aoi
    if year:
        return data_dir / f"{aoi}_{product}_{year}.{ext}"
    return data_dir / f"{aoi}_{product}.{ext}"


def _standard_path_daily(aoi: str, product: str, year_start: int, year_end: int) -> Path:
    """Path for multi-year daily NC output (e.g. ghana_chirps_rainfall_daily_2024_2025_env.nc)."""
    data_dir = _REPO_ROOT / "data" / aoi
    return data_dir / f"{aoi}_{product}_{year_start}_{year_end}_env.nc"



def run_download(
    aoi: str,
    datasets: list[str] | None = None,
    outputs: list[str] | None = None,
    years: list[int] | None = None,
    months: list[str] | None = None,
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
    for name, spec in selected.items():
        log.info("Downloading: %s", name)
        if not _check_auth(spec):
            results[name] = {"status": "skipped", "reason": "auth missing"}
            continue

        try:
            for output_name, func in spec.outputs.items():
                if outputs and output_name not in outputs:
                    continue

                log.info("  %s.%s", name, output_name)
                is_ts = spec.is_time_series
                required_for_abm = True  # TODO: propagate from DownloaderSpec in future

                if is_ts:
                    if not years:
                        log.warning("    %s is time-series but no years specified — skipping", output_name)
                        continue

                    result = func(aoi=aoi_obj, years=years, months=months, cache_dir=cache)

                    if result is None:
                        continue

                    # Determine output format from spec.formats
                    fmt = spec.formats.get(output_name) if spec.formats else None

                    if fmt == "daily":
                        # Daily: write entire multi-year result as ONE NC file
                        path = _standard_path_daily(aoi, output_name, min(years), max(years))
                        save_product(result, path, format="nc")
                        update_dataset(
                            aoi,
                            spec.manifest_keys[output_name],
                            None,
                            path.name,
                            period={"start": f"{min(years)}-01-01", "end": f"{max(years)}-12-31"},
                            type="time-series",
                            required_for_abm=required_for_abm,
                        )
                        log.info("    %s → %s (daily NC)", output_name, path.name)
                    else:
                        # Monthly / default: slice by year/month, write TIF per month
                        has_time = "time" in result.dims or "valid_time" in result.dims
                        if has_time:
                            time_dim = "valid_time" if "valid_time" in result.dims else "time"
                            for yr in years:
                                sel = result.sel({time_dim: result[time_dim].dt.year == yr})
                                for mo in (months or range(1, 13)):
                                    month_int = int(mo)
                                    slc = sel.sel({time_dim: sel[time_dim].dt.month == month_int})
                                    ext = ".nc" if isinstance(slc, xr.Dataset) else ".tif"
                                    path = _standard_path(aoi, output_name, yr, ext.lstrip("."))
                                    save_product(slc, path)
                                    update_dataset(
                                        aoi,
                                        spec.manifest_keys[output_name],
                                        yr,
                                        path.name,
                                        type="time-series",
                                        required_for_abm=required_for_abm,
                                    )
                                    log.info("    %s/%02d → %s", yr, month_int, path.name)
                        else:
                            # Single (year, month) — 2D result, no time dim
                            yr = years[0]
                            ext = ".nc" if isinstance(result, xr.Dataset) else ".tif"
                            path = _standard_path(aoi, output_name, yr, ext.lstrip("."))
                            save_product(result, path)
                            update_dataset(
                                aoi,
                                spec.manifest_keys[output_name],
                                yr,
                                path.name,
                                type="time-series",
                                required_for_abm=required_for_abm,
                            )
                            log.info("    %s → %s", yr, path.name)
                else:
                    result = func(aoi=aoi_obj, cache_dir=cache)

                    if result is None:
                        continue

                    ext = ".nc" if isinstance(result, xr.Dataset) else ".tif"
                    path = _standard_path(aoi, output_name, None, ext.lstrip("."))
                    save_product(result, path)
                    update_dataset(
                        aoi,
                        spec.manifest_keys[output_name],
                        None,
                        path.name,
                        type="static",
                        required_for_abm=required_for_abm,
                    )
                    log.info("    → %s", path.name)

            results[name] = {"status": "ok"}
        except Exception as e:
            log.error("Download failed for %s: %s", name, e)
            results[name] = {"status": "error", "error": str(e)}

    return results
