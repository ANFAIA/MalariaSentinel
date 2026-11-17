"""Download plugin registry — discovers DOWNLOADER dicts from mal_commonlib loaders."""

import importlib
import logging
import pkgutil
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

log = logging.getLogger(__name__)

def _loader_module_names() -> list[str]:
    """Scan the loaders package: every module with a DOWNLOADER dict is a plugin.

    Replaces the old hardcoded LOADER_MODULES list — a loader file dropped
    in mal_commonlib/data/loaders/ is registered just by existing (the list
    silently missed ``worldcover.py``). The per-module tolerance in
    :func:`discover_downloaders` keeps utility modules (no DOWNLOADER) and
    import failures from breaking the registry.
    """
    import mal_commonlib.data.loaders as loaders_pkg

    return [
        info.name
        for info in pkgutil.iter_modules(loaders_pkg.__path__)
        if not info.ispkg and info.name != "__init__"
    ]


@dataclass
class DownloaderSpec:
    """Description of one dataset that can be downloaded for an AOI.

    Mirrors the ``DOWNLOADER`` dict exported by a loader module: the
    dataset name, its outputs (callables) and the manifest key under which
    each output is registered, plus the metadata used by the runner
    (time series flag, formats, authentication, licence).
    """

    name: str
    description: str
    requires_auth: list[str]
    outputs: dict[str, Callable]
    manifest_keys: dict[str, str]
    module_name: str
    is_time_series: bool = False
    formats: dict[str, str] | None = None
    abm_default_outputs: list[str] | None = None
    required_for_abm: dict[str, bool] | None = None
    reductions: dict[str, str] | None = None
    license: str | None = None
    attribution: str | None = None


def discover_downloaders() -> dict[str, DownloaderSpec]:
    """Collect the downloader plugins exported by the loader modules.

    Every module of ``mal_commonlib.data.loaders`` is imported and its
    ``DOWNLOADER`` dict, if present, is turned into a DownloaderSpec keyed
    by dataset name. Modules without a ``DOWNLOADER`` and modules that
    fail to import are skipped with a warning.

    Returns:
        Mapping of dataset name to its spec.
    """
    registry: dict[str, DownloaderSpec] = {}
    for mod_name in _loader_module_names():
        try:
            mod = importlib.import_module(f"mal_commonlib.data.loaders.{mod_name}")
            raw = getattr(mod, "DOWNLOADER", None)
            if raw is None:
                continue
            profile_defaults = {
                # --- env tensor (ingest/daily_nc.py, contract v3.0) ---
                "chirps": ["rainfall_daily"],
                "era5": ["air_temp_daily", "wind_6hourly"],
                "jrc_gsw": ["habitat_features"],
                "dynamic_world": ["class_fractions"],
                # --- static habitat gpkg (ingest/env.py) ---
                # dem/modis retired: no terrain or NDVI consumer in the
                # redesign's contract (plan 01 §6-§7).
                # --- host density (ingest/hosts.py) ---
                "worldpop": ["population"],
                "glw": ["cattle", "goats", "sheep", "pigs", "chickens"],
                "ghsl": ["urban_class"],
                "buildings": ["building_fraction"],
                "wildlife": ["wildlife_host_proxy"],
                # --- saltwater filter (ingest/daily_nc.py) ---
                "coastline": ["land_mask"],
                # --- explicitly excluded (not ABM defaults) ---
                "hydrorivers": [],
                "smap": [],
            }
            profile_formats = {
                "era5": {"air_temp_daily": "daily", "wind_6hourly": "daily"},
                "chirps": {"rainfall_daily": "daily"},
                # "daily" here only selects the runner's multi-year-NC
                # writer: DW class_fractions is one frame per run year.
                "dynamic_world": {"class_fractions": "daily"},
            }
            spec = DownloaderSpec(
                name=raw["name"],
                description=raw.get("description", ""),
                requires_auth=raw.get("requires_auth", []),
                outputs=raw.get("outputs", {}),
                manifest_keys=raw.get("manifest_keys", {}),
                module_name=mod_name,
                is_time_series=raw.get("is_time_series", False),
                formats=raw.get("formats", profile_formats.get(raw["name"])),
                abm_default_outputs=raw.get(
                    "abm_default_outputs", profile_defaults.get(raw["name"])
                ),
                required_for_abm=raw.get("required_for_abm", None),
                reductions=raw.get("reductions", None),
                license=raw.get("license", None),
                attribution=raw.get("attribution", None),
            )
            registry[spec.name] = spec
            log.debug(
                "Registered downloader: %s (%d outputs)", spec.name, len(spec.outputs)
            )
        except Exception as e:
            log.warning("Failed to load downloader from %s: %s", mod_name, e)
    return registry


def list_downloaders() -> list[dict[str, Any]]:
    """Summarise the available downloaders as name, description and outputs."""
    registry = discover_downloaders()
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "outputs": list(spec.outputs.keys()),
        }
        for spec in registry.values()
    ]
