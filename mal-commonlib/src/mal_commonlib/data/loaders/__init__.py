"""Data loaders for the M1.3a env channels and host density layers."""

from .jrc_gsw import load_jrc_gsw_water_frac
from .worldpop import load_worldpop_population
from .glw import load_glw_livestock
from .ghsl import load_ghsl_urban_class
from .wildlife import load_wildlife_host_proxy
from .buildings import load_buildings_fraction

# Deprecated class-style shims (kept for backward compatibility)
from .worldpop import WorldPopLoader
from .glw import GLWLoader
from .ghsl import GHSLLoader
from .wildlife import WildlifeLoader
from .buildings import BuildingsLoader

__all__ = [
    "load_jrc_gsw_water_frac",
    "load_worldpop_population",
    "load_glw_livestock",
    "load_ghsl_urban_class",
    "load_wildlife_host_proxy",
    "load_buildings_fraction",
    "WorldPopLoader",
    "GLWLoader",
    "GHSLLoader",
    "WildlifeLoader",
    "BuildingsLoader",
]
