"""Download plugin registry — discovers DOWNLOADER dicts from mal_commonlib loaders."""
import importlib
import logging
from dataclasses import dataclass
from typing import Any, Callable

log = logging.getLogger(__name__)

LOADER_MODULES = [
    "era5", "chirps", "dem", "jrc_gsw", "modis",
    "worldpop", "glw", "ghsl", "wildlife", "buildings",
    "hydrolakes", "hydrorivers", "worldcover",
    "smap",
]

@dataclass
class DownloaderSpec:
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

def discover_downloaders() -> dict[str, DownloaderSpec]:
    registry: dict[str, DownloaderSpec] = {}
    for mod_name in LOADER_MODULES:
        try:
            mod = importlib.import_module(f"mal_commonlib.data.loaders.{mod_name}")
            raw = getattr(mod, "DOWNLOADER", None)
            if raw is None:
                continue
            profile_defaults = {
                # --- env tensor (ingest/env.py) ---
                "chirps": ["rainfall_daily"],
                "era5": ["water_temp", "wind_6hourly"],
                "jrc_gsw": ["water_occurrence"],
                "modis": ["ndvi"],
                "hydrolakes": ["permanent_lakes"],
                # --- habitat patches (ingest/env.py) ---
                "dem": ["elevation"],
                # --- host density (ingest/hosts.py) ---
                "worldpop": ["population"],
                "glw": ["cattle", "goats", "sheep", "pigs", "chickens"],
                "ghsl": ["urban_class"],
                "buildings": ["building_fraction"],
                "wildlife": ["wildlife_host_proxy"],
                # --- explicitly excluded (not ABM defaults) ---
                "hydrorivers": [],
                "worldcover": [],
                "smap": [],
            }
            profile_formats = {
                "era5": {"wind_6hourly": "daily", "water_temp": "monthly"},
                "chirps": {"rainfall": "monthly", "rainfall_daily": "daily"},
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
                abm_default_outputs=raw.get("abm_default_outputs", profile_defaults.get(raw["name"])),
                required_for_abm=raw.get("required_for_abm", None),
                reductions=raw.get("reductions", None),
            )
            registry[spec.name] = spec
            log.debug("Registered downloader: %s (%d outputs)", spec.name, len(spec.outputs))
        except Exception as e:
            log.warning("Failed to load downloader from %s: %s", mod_name, e)
    return registry

def list_downloaders() -> list[dict[str, Any]]:
    registry = discover_downloaders()
    return [
        {"name": spec.name, "description": spec.description, "outputs": list(spec.outputs.keys())}
        for spec in registry.values()
    ]
