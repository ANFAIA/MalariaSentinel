"""Download runner — orchestrates downloads for an AOI via the plugin registry."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

from .registry import discover_downloaders, DownloaderSpec
from .manifest import update_manifest

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

def run_download(
    aoi: str,
    datasets: list[str] | None = None,
    outputs: list[str] | None = None,
    years: list[int] | None = None,
    months: list[str] | None = None,
    output_dir: str | Path | None = None,
    **kwargs,
) -> dict[str, Any]:
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

                call_kwargs: dict[str, Any] = {"aoi": aoi}
                if years:
                    call_kwargs["years"] = years
                if months:
                    call_kwargs["months"] = months

                ext = ".nc" if "wind" in output_name else ".tif"
                call_kwargs["output_path"] = out_dir / f"{aoi}_{output_name}{ext}"

                func(**call_kwargs)

                manifest_key = spec.manifest_keys.get(output_name, output_name)
                update_manifest(aoi, manifest_key, Path(call_kwargs["output_path"]).name)

            results[name] = {"status": "ok"}
        except Exception as e:
            log.error("Download failed for %s: %s", name, e)
            results[name] = {"status": "error", "error": str(e)}

    return results
