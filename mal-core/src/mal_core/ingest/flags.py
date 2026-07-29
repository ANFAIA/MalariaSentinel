from typing import Any, TypedDict


class IngestFlags(TypedDict, total=False):
    aoi: str
    year: int
    month: int
    scale: str
    skip_era5: bool
    skip_modis: bool
    skip_jrc_gsw: bool
    format: str
    # Hosts-specific
    what: str  # "env", "hosts", "mobility", "all"
    worldpop_year: int
    skip_buildings: bool
    skip_wildlife: bool
    # Mobility-specific
    cell_size_km: float
    beta_day: float
    beta_night: float
    beta_livestock: float
    max_distance_km: float


INGEST_FLAGS_SCHEMA: dict[str, dict[str, Any]] = {
    "aoi": {"type": str, "default": "ghana", "help": "AOI slug"},
    "year": {"type": int, "default": 2024, "help": "Year"},
    "month": {"type": int, "default": 1, "help": "Month (1-12)"},
    "scale": {"type": str, "default": "regional", "help": "Scale level"},
    "what": {"type": str, "default": "all", "help": "What to build: env, hosts, mobility, all"},
    "skip_era5": {"type": bool, "default": False, "help": "Skip ERA5 download"},
    "skip_modis": {"type": bool, "default": False, "help": "Skip MODIS download"},
    "skip_jrc_gsw": {"type": bool, "default": False, "help": "Skip JRC GSW download"},
    "format": {"type": str, "default": "tif", "help": "Output format (tif/nc)"},
    "worldpop_year": {"type": int, "default": 2019, "help": "WorldPop year"},
    "skip_buildings": {"type": bool, "default": False, "help": "Skip Overture buildings"},
    "skip_wildlife": {"type": bool, "default": False, "help": "Skip wildlife host proxy"},
    "cell_size_km": {"type": float, "default": 1.0, "help": "Grid cell size in km"},
    "beta_day": {"type": float, "default": 0.05, "help": "Human daytime mobility friction"},
    "beta_night": {"type": float, "default": 0.5, "help": "Human nighttime mobility friction"},
    "beta_livestock": {"type": float, "default": 0.1, "help": "Livestock mobility friction"},
    "max_distance_km": {"type": float, "default": 50.0, "help": "Max mobility distance"},
}
