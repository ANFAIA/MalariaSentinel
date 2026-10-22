"""Data loaders for the env channels, habitat statics, hosts and mobility.

Plugin modules — each exports a public ``load_*`` function and a
``DOWNLOADER`` dict consumed by ``mal_core.download.registry`` (pkgutil
scan, no manual list). Contract v3.0: the four land-cover statics
(``lc_built/lc_wetland/lc_open_plus_water/lc_crop``) come from Google
Dynamic World V1 (per-year modal label composites on Earth Engine); the
persistent-water plane stays JRC GSW. The WorldCover/DEM/annual-ERA5
loaders are retired (git history).
"""
from .era5 import load_era5_air_temp_daily, load_era5_wind_6hourly
from .jrc_gsw import load_jrc_gsw_habitat_features
from .dynamic_world import load_dw_class_fractions
from .dynamic_world import load_dw_label_mode  # shared utility (wildlife)
from .chirps import load_chirps_rainfall_daily
from .coastline import load_coastline_land_mask
from .worldpop import load_worldpop_population
from .glw import load_glw_livestock
from .ghsl import load_ghsl_urban_class
from .buildings import load_buildings_fraction
from .wildlife import load_wildlife_host_proxy
from .smap import load_smap_salinity

__all__ = [
    "load_era5_air_temp_daily",
    "load_era5_wind_6hourly",
    "load_jrc_gsw_habitat_features",
    "load_dw_class_fractions",
    "load_dw_label_mode",
    "load_chirps_rainfall_daily",
    "load_coastline_land_mask",
    "load_worldpop_population",
    "load_glw_livestock",
    "load_ghsl_urban_class",
    "load_buildings_fraction",
    "load_wildlife_host_proxy",
    "load_smap_salinity",
]