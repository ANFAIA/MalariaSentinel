"""Data loaders for the M1.3a env channels (CHIRPS, ERA5, MODIS, MERIT DEM, ESA WorldCover / JRC GSW)."""

from .jrc_gsw import load_jrc_gsw_water_frac
from .worldcover import load_worldcover_water_frac

__all__ = [
    "load_jrc_gsw_water_frac",
    "load_worldcover_water_frac",
]
