"""MalariaSentinel — shared utilities, config, and paths."""
__version__ = "0.1.0"

from mal_commonlib.aoi import AOI, Scale  # M1.2a: region-agnostic Area of Interest

__all__ = [
    "AOI",
    "Scale",
]