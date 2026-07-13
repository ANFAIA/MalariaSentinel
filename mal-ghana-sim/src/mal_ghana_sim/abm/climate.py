"""Climate engine facade for the M1 ABM thin slice.

A thin layer over the M1.3a env tensor (the 4-band COG emitted by
``scripts.build_env``). For the thin slice the engine uses *constant*
values per day (the env tensor is monthly; daily interpolation is a
``[M7+]`` concern). The API surface is the contract ``AnophelesABM``
consumes; the implementation can be swapped to a real xarray lookup
in M2+ without touching the model.

Two API tiers are exposed:

* **Point lookups** (``get_rain_daily``, ``get_water_temp_c``,
  ``get_water_frac``, ``get_ndvi``) — per-patch calls used by the
  old per-agent ``model.py``. Kept for backward compatibility.
* **Grid accessors** (``rain_daily_grid``, ``temp_suitability_grid``,
  ``water_frac_grid``, ``ndvi_grid``) — return the *full* ``(H, W)``
  numpy array for a given day, used by the M1.5 ``CoordinatorModel``
  to build the per-patch state in a single pass without per-patch
  Python calls.
"""
from __future__ import annotations

from datetime import date as _date

import numpy as np


class ClimateEngine:
    """Thin facade over the M1.3a env tensor.

    Parameters
    ----------
    env : dict
        A dictionary with one of the following shapes (synthetic / real):
          * Synthetic (``env["synthetic"] is True``): keys ``"rain_daily"``,
            ``"water_temp_c"``, ``"water_frac"``, ``"ndvi"`` — each either a
            callable ``f(date, lon, lat) -> float`` or a scalar.
          * Real: keys ``"rain_daily"`` (xr.DataArray), ``"water_temp_c``
            (xr.DataArray), ``"water_frac`` (xr.DataArray),
            ``"ndvi`` (xr.DataArray). The M2+ implementation does
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

    # -- grid accessors (M1.5) ---------------------------------------------

    def _grid_for_key(self, key: str, h: int, w: int) -> np.ndarray:
        """Build a ``(H, W)`` grid for the named climate key.

        Resolution rules:
          * **scalar** → broadcast to (H, W).
          * **callable** → vectorise over a meshgrid of (lon, lat)
            using the AOI bbox (resolution is per-degree so the call
            is cheap; the per-cell evaluation is ``O(H*W)`` Python
            calls which dominates for a thin slice but is still well
            under a second on a 30k-cell AOI).
          * **xr.DataArray / 2D numpy array** → return as-is (must
            already be (H, W) and EPSG:4326-aligned).
        """
        v = self.env.get(key)
        if v is None:
            return np.zeros((h, w), dtype=np.float32)
        if callable(v):
            # We need an AOI bbox to evaluate the callable; in the
            # thin slice the ``env`` dict's callables are constant per
            # day so the lat/lon arguments are ignored. The M1.5 facade
            # passes a zero-valued lon/lat meshgrid which the callable
            # can ignore.
            lon_mesh, lat_mesh = self._meshgrid(h, w)
            flat = np.vectorize(
                lambda lon, lat: float(v(_date(2000, 1, 1), float(lon), float(lat))),
                otypes=[np.float32],
            )
            return flat(lon_mesh, lat_mesh).astype(np.float32, copy=False)
        try:
            arr = np.asarray(v, dtype=np.float32)
        except Exception:
            return np.zeros((h, w), dtype=np.float32)
        if arr.ndim == 0:
            return np.broadcast_to(arr, (h, w)).astype(np.float32, copy=False)
        if arr.ndim == 1 and arr.shape[0] == h * w:
            return arr.reshape(h, w).astype(np.float32, copy=False)
        if arr.shape == (h, w):
            return arr.astype(np.float32, copy=False)
        # Fallback: mean-pool to a constant grid.
        return np.broadcast_to(arr.mean(), (h, w)).astype(np.float32, copy=False)

    @staticmethod
    def _meshgrid(h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
        """Build a 1 deg-spaced ``(H, W)`` meshgrid centred on (0, 0).

        The synthetic env callables are constant per day, so the
        actual lon/lat values do not matter; we use a coarse grid
        just to give the callable something to vectorise over. The
        M1.5 facade does not depend on these values for the per-patch
        activation logic — the per-patch lookup uses the env callable
        directly with the patch's lon/lat.
        """
        lat = np.linspace(-1.0, 1.0, h, dtype=np.float32)
        lon = np.linspace(-1.0, 1.0, w, dtype=np.float32)
        return np.meshgrid(lon, lat)

    def rain_daily_grid(self, day, h: int, w: int) -> np.ndarray:
        """Return the ``(H, W)`` daily rainfall grid for ``day``."""
        return self._grid_for_key("rain_daily", h, w)

    def temp_suitability_grid(self, day, h: int, w: int) -> np.ndarray:
        """Return the ``(H, W)`` water-temperature grid for ``day``."""
        return self._grid_for_key("water_temp_c", h, w)

    def water_frac_grid(self, h: int, w: int) -> np.ndarray:
        """Return the ``(H, W)`` water-frac grid (static)."""
        return self._grid_for_key("water_frac", h, w)

    def ndvi_grid(self, h: int, w: int) -> np.ndarray:
        """Return the ``(H, W)`` NDVI grid (static)."""
        return self._grid_for_key("ndvi", h, w)
