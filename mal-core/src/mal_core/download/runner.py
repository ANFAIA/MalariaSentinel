"""Download runner — orchestrates downloads for an AOI via the plugin registry."""
from __future__ import annotations
import inspect
import logging
from pathlib import Path
from typing import Any

import xarray as xr

from .registry import discover_downloaders, DownloaderSpec
from .manifest import update_dataset, validate_completeness
from .writer import save_product

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]

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
    """Determine standard file path per data-format-spec.md naming convention."""
    data_dir = _REPO_ROOT / "data" / aoi
    if year:
        return data_dir / f"{aoi}_{product}_{year}.{ext}"
    return data_dir / f"{aoi}_{product}.{ext}"

def _is_time_series(spec: DownloaderSpec, output_name: str) -> bool:
    """A loader output is time-series if `year` is a REQUIRED param (no default)."""
    func = spec.outputs.get(output_name)
    if func is None:
        return False
    sig = inspect.signature(func)
    params = sig.parameters
    if "year" not in params:
        return False
    return params["year"].default is inspect.Parameter.empty

def run_download(
    aoi: str,
    datasets: list[str] | None = None,
    outputs: list[str] | None = None,
    years: list[int] | None = None,
    months: list[str] | None = None,
    output_dir: str | Path | None = None,
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

    results = {}
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

                # Determine if time-series or static
                is_ts = _is_time_series(spec, output_name)

                # Build all possible kwargs, then filter to what the loader accepts
                sig = inspect.signature(func)
                accepted = set(sig.parameters.keys())

                if is_ts and years:
                    for year in years:
                        all_kwargs = {
                            "aoi": aoi_obj,
                            "year": year,
                            "years": [year],
                            "month": int(months[0]) if months else None,
                            "months": months,
                        }
                        call_kwargs = {k: v for k, v in all_kwargs.items() if k in accepted and v is not None}
                        result = func(**call_kwargs)
                        if result is not None:
                            ext = ".nc" if isinstance(result, xr.Dataset) else ".tif"
                            path = _standard_path(aoi, output_name, year, ext.lstrip("."))
                            save_product(result, path)
                            manifest_key = spec.manifest_keys[output_name]
                            update_dataset(aoi, manifest_key, year, path.name)
                            log.info("    %s → %s", year, path.name)
                else:
                    all_kwargs = {
                        "aoi": aoi_obj,
                    }
                    call_kwargs = {k: v for k, v in all_kwargs.items() if k in accepted and v is not None}
                    result = func(**call_kwargs)
                    if result is not None:
                        ext = ".nc" if isinstance(result, xr.Dataset) else ".tif"
                        path = _standard_path(aoi, output_name, None, ext.lstrip("."))
                        save_product(result, path)
                        manifest_key = spec.manifest_keys[output_name]
                        update_dataset(aoi, manifest_key, None, path.name)
                        log.info("    → %s", path.name)

            results[name] = {"status": "ok"}
        except Exception as e:
            log.error("Download failed for %s: %s", name, e)
            results[name] = {"status": "error", "error": str(e)}

    return results
