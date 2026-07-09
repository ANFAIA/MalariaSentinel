"""Climate engine facade for the M1 ABM thin slice.

A thin layer over the M1.3a env tensor (the 4-band COG emitted by
``scripts.build_env``). For the thin slice the engine uses *constant*
values per day (the env tensor is monthly; daily interpolation is a
``[M7+]`` concern). The API surface is the contract ``AnophelesABM``
consumes; the implementation can be swapped to a real xarray lookup
in M2+ without touching the model.
"""
from __future__ import annotations

from datetime import date as _date


class ClimateEngine:
    """Thin facade over the M1.3a env tensor.

    Parameters
    ----------
    env : dict
        A dictionary with one of the following shapes (synthetic / real):
          * Synthetic (``env["synthetic"] is True``): keys ``"rain_daily"``,
            ``"water_temp_c"``, ``"water_frac"``, ``"ndvi"`` — each either a
            callable ``f(date, lon, lat) -> float`` or a scalar.
          * Real: keys ``"rain_daily"`` (xr.DataArray), ``"water_temp_c"``
            (xr.DataArray), ``"water_frac"`` (xr.DataArray),
            ``"ndvi"`` (xr.DataArray). The M2+ implementation does
            nearest-neighbour lookups; for M1 we expose the same call
            surface with a synthetic fallback.

    The thin slice is deterministic for a given ``(date, lon, lat)``
    (no day-of-year variation in the synthetic path). This is documented
    in ``docs/abm-mesa-geo-adaptation.md`` §3 (M1 uses T2m as a proxy
    for water temperature and does not interpolate daily CHIRPS).
    """

    def __init__(self, env: dict) -> None:
        self.env = env

    def _lookup(self, key: str, date, lon: float, lat: float) -> float:
        """Resolve a climate value at (date, lon, lat) from the env dict."""
        v = self.env.get(key)
        if v is None:
            return 0.0
        if callable(v):
            return float(v(date, float(lon), float(lat)))
        # xr.DataArray path: nearest-neighbour lookup (M1 just returns the
        # mean — the thin slice does not need pixel-precise answers).
        try:
            import numpy as np
            return float(np.asarray(v).mean())
        except Exception:
            return float(v)

    def get_rain_daily(self, date, lon: float, lat: float) -> float:
        """Daily rainfall in mm (synthetic: constant per day for M1)."""
        return self._lookup("rain_daily", date, lon, lat)

    def get_water_temp_c(self, date, lon: float, lat: float) -> float:
        """Shallow-water temperature in C (synthetic: constant for M1)."""
        return self._lookup("water_temp_c", date, lon, lat)

    def get_water_frac(self, lon: float, lat: float) -> float:
        """Fraction of the cell covered by open water (∈ [0, 1])."""
        return self._lookup("water_frac", _date(2000, 1, 1), lon, lat)

    def get_ndvi(self, lon: float, lat: float) -> float:
        """NDVI rescaled to [0, 1]."""
        return self._lookup("ndvi", _date(2000, 1, 1), lon, lat)
