from typing import TypedDict, Any

class IngestFlags(TypedDict, total=False):
    aoi: str
    year: int
    month: int
    scale: str
    skip_era5: bool
    skip_modis: bool
    skip_jrc_gsw: bool
    format: str

INGEST_FLAGS_SCHEMA: dict[str, dict[str, Any]] = {
    "aoi": {"type": str, "default": "ghana", "help": "AOI slug"},
    "year": {"type": int, "default": 2024, "help": "Year"},
    "month": {"type": int, "default": 1, "help": "Month (1-12)"},
    "scale": {"type": str, "default": "regional", "help": "Scale level"},
    "skip_era5": {"type": bool, "default": False, "help": "Skip ERA5 download"},
    "skip_modis": {"type": bool, "default": False, "help": "Skip MODIS download"},
    "skip_jrc_gsw": {"type": bool, "default": False, "help": "Skip JRC GSW download"},
    "format": {"type": str, "default": "tif", "help": "Output format (tif/nc)"},
}
