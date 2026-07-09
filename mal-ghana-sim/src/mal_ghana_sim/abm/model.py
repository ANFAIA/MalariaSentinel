"""Anopheles ABM model for the M1 thin slice.

Mesa-Geo v0.9.3 / Mesa 3.5.1 ``mesa.Model`` subclass. Orchestrates
``HabitatPatch`` activation, ``MosquitoAgent`` lifecycle (larva ->
adult), EIP accumulation, and the monthly state COG snapshot per
``docs/abm-output-contract.md`` v1.0 §1.

The model is **deterministic for a given seed**. All stochastic draws
go through ``self.rng`` (numpy ``Generator``), and the scheduler
shim's per-step shuffle re-seeds from ``self.rng`` too.

Suitability (v1, M1): a cell is suitable (1.0) iff at least one
``HabitatPatch`` is currently ``activated`` at that cell. All other
cells are 0.0. The cell index is derived from the patch's
``(row, col)`` attribute on the gpkg; if the gpkg lacks it we fall
back to the patch's lon/lat and the AOI's transform.
"""
from __future__ import annotations

import json
from datetime import date

import mesa
import mesa_geo
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import Point

from .agents import MosquitoAgent
from .climate import ClimateEngine
from .eip import accumulate_eip
from .habitat import HabitatPatch
from .habitat_engine import HabitatEngine
from .scheduler import RandomActivationByTypeShim

CONTRACT_VERSION: str = "1.0"
GENERATOR_VERSION: str = "m1-thin-0.1.0"
NODATA_SENTINEL: float = -9999.0
STATE_BAND_NAMES: tuple[str, ...] = ("density", "suitability")


class AnophelesABM(mesa.Model):
    """M1 thin-slice ABM (Mesa-Geo v0.9.3, 2 stages, PLUVIAL_POOL)."""

    K_MAX: int = 1000

    def __init__(
        self,
        aoi,
        env: dict,
        habitat_patches_gdf,
        *,
        seed: int = 42,
        start_date: date | None = None,
    ) -> None:
        super().__init__()
        self.aoi = aoi
        self.env = env
        self.current_date: date | None = start_date
        self.rng = np.random.default_rng(int(seed))
        # Mesa 3.5.1's mesa.Model.__init__ creates self.random (stdlib) and
        # self.rng (numpy). The shim uses self.rng; we keep both references
        # in sync for compatibility.
        self.schedule = RandomActivationByTypeShim(self)
        self.habitat_engine = HabitatEngine(aoi, habitat_patches_gdf)
        self.habitat_engine.materialise(self)
        self.climate = ClimateEngine(env)
        self.geospace = mesa_geo.GeoSpace(crs="EPSG:4326")
        self._cell_lookup: dict[int, int] = {}
        self._build_cell_lookup()
        self._seed_initial_population()

    # -- cell index helpers --------------------------------------------------

    def _build_cell_lookup(self) -> None:
        """Map each patch to its (row, col) cell on the AOI grid.

        Reads the ``row``/``col`` columns from the gpkg if present
        (the M1.3b ``build_env`` writes them); otherwise derives them
        from the patch's geometry and the AOI's transform.
        """
        h, w = self.aoi.cells_per_side()
        transform = from_bounds(*self.aoi.bbox, w, h)
        for idx, patch in enumerate(self.habitat_engine.patches):
            row = col = None
            row_series = self.habitat_engine.gdf.iloc[idx].get("row")
            col_series = self.habitat_engine.gdf.iloc[idx].get("col")
            if row_series is not None and col_series is not None:
                try:
                    row = int(row_series); col = int(col_series)
                except (TypeError, ValueError):
                    row = col = None
            if row is None or col is None:
                geom = patch.geometry
                if isinstance(geom, Point):
                    from rasterio.transform import rowcol
                    r, c = rowcol(transform, geom.x, geom.y)
                    row, col = int(r), int(c)
            if row is None or col is None:
                continue
            self._cell_lookup[idx] = row * w + col

    def _cell_for_patch(self, patch: HabitatPatch) -> int | None:
        """Linear (row, col) index of the patch's cell, or None."""
        for idx, p in enumerate(self.habitat_engine.patches):
            if p is patch:
                return self._cell_lookup.get(idx)
        return None

    # -- initial population --------------------------------------------------

    def _seed_initial_population(self) -> None:
        """Seed 30% of K larvae at each patch (thin-slice warm start)."""
        for patch in self.habitat_engine.patches:
            n_seed = max(0, int(round(0.3 * int(patch.K))))
            for _ in range(n_seed):
                geom = patch.geometry
                if geom is None or geom.is_empty:
                    geom = Point(0.0, 0.0)
                # Reuse the patch's geometry for the larva — M1 keeps the
                # agent's location colocated with its origin patch.
                larva = MosquitoAgent(self, geom, str(patch.crs))
                larva.origin_patch = patch
                self.schedule.add(larva, type_key=_LARVA_KEY)

    # -- per-day dynamics ----------------------------------------------------

    def _activate_habitats(self, day: date) -> None:
        """Update ``patch.activated`` from climate for the given day."""
        for patch in self.habitat_engine.patches:
            if patch.geometry is None or patch.geometry.is_empty:
                continue
            cx, cy = patch.geometry.x, patch.geometry.y
            rain = self.climate.get_rain_daily(day, cx, cy)
            water_temp = self.climate.get_water_temp_c(day, cx, cy)
            patch.activate(rain, water_temp)

    def _step_habitats(self, day: date) -> None:
        """Activate patches then apply density-dependent mortality + pupation.

        Larvae are accounted in bulk per patch (one ``produce_adults``
        call per patch) so the model's per-day cost is O(P) where P is
        the number of patches, not O(N_larvae).
        """
        self._activate_habitats(day)
        for patch in self.habitat_engine.patches:
            larvae_here = [
                a for a in self.schedule.agents_by_type.get(_LARVA_KEY, [])
                if a.origin_patch is patch
            ]
            N = len(larvae_here)
            if N == 0:
                continue
            dead = patch.mortality(N, density_dep=True)
            survivors = larvae_here[dead:] if dead > 0 else larvae_here
            if dead > 0:
                for agent in larvae_here[:dead]:
                    self.schedule.remove(agent, type_key=_LARVA_KEY)
            emerged = patch.produce_adults(len(survivors), self)
            for agent in survivors[:emerged]:
                agent.stage = "adult"
                self.schedule.remove(agent, type_key=_LARVA_KEY)
                self.schedule.add(agent, type_key=_ADULT_KEY)
            # Survivors that did not emerge stay as larvae for another day.

    def _step_adults(self, day: date) -> None:
        """Accumulate EIP per adult and apply local dispersal.

        The thin slice treats EIP accumulation as a model-level loop
        (a per-adult loop inside ``_step_adults``) so it benefits from
        ``self.rng`` reproducibility and is easy to assert in tests.
        """
        adults = list(self.schedule.agents_by_type.get(_ADULT_KEY, []))
        if not adults:
            return
        for adult in adults:
            if adult.geometry is None or adult.geometry.is_empty:
                continue
            cx, cy = adult.geometry.x, adult.geometry.y
            water_temp = self.climate.get_water_temp_c(day, cx, cy)
            adult.eip_progress = accumulate_eip(adult.eip_progress, water_temp)
            # 20% chance to disperse on any given day (rural gambiae).
            if self.rng.random() < 0.2:
                adult._local_disperse(self.rng, sigma_m=1000.0, max_distance_m=2000.0)

    def step(self) -> None:
        """Advance the model by one day.

        Per-day schedule:
            1. Activate habitat patches from climate.
            2. Run density-dependent mortality + pupation (larva->adult).
            3. Accumulate EIP + apply local dispersal on adults.
            4. Tick the scheduler shim (one ``.step()`` per agent).
        """
        if self.current_date is None:
            from datetime import date as _date
            self.current_date = _date(2000, 1, 1)
        self._step_habitats(self.current_date)
        self._step_adults(self.current_date)
        self.schedule.step()
        # Advance the clock by one day.
        from datetime import timedelta
        self.current_date = self.current_date + timedelta(days=1)

    # -- snapshot ------------------------------------------------------------

    def _active_cells(self) -> set[int]:
        """Linear indices of cells with at least one active patch (v1 suitability)."""
        active: set[int] = set()
        for idx, patch in enumerate(self.habitat_engine.patches):
            if patch.activated and idx in self._cell_lookup:
                active.add(self._cell_lookup[idx])
        return active

    def _density_grid(self, h: int, w: int) -> np.ndarray:
        """Build the (H, W) density grid (sum of agents per cell, normalised by K_MAX)."""
        grid = np.zeros((h, w), dtype=np.float32)
        # Larvae (counted at their origin patch's cell).
        for larva in self.schedule.agents_by_type.get(_LARVA_KEY, []):
            if larva.origin_patch is None:
                continue
            for idx, patch in enumerate(self.habitat_engine.patches):
                if patch is larva.origin_patch and idx in self._cell_lookup:
                    rc = self._cell_lookup[idx]
                    r, c = divmod(rc, w)
                    if 0 <= r < h and 0 <= c < w:
                        grid[r, c] += 1.0
                    break
        # Adults (counted at their current geometry's cell).
        transform = from_bounds(*self.aoi.bbox, w, h)
        from rasterio.transform import rowcol
        for adult in self.schedule.agents_by_type.get(_ADULT_KEY, []):
            if adult.geometry is None or adult.geometry.is_empty:
                continue
            try:
                r, c = rowcol(transform, adult.geometry.x, adult.geometry.y)
            except Exception:
                continue
            r = int(r); c = int(c)
            if 0 <= r < h and 0 <= c < w:
                grid[r, c] += 1.0
        return np.clip(grid / float(self.K_MAX), 0.0, 1.0).astype(np.float32)

    def _suitability_grid(self, h: int, w: int) -> np.ndarray:
        """Build the (H, W) suitability grid (1.0 for cells with an active patch)."""
        active = self._active_cells()
        grid = np.zeros((h, w), dtype=np.float32)
        for rc in active:
            r, c = divmod(rc, w)
            if 0 <= r < h and 0 <= c < w:
                grid[r, c] = 1.0
        return grid

    def snapshot(self, path: str, *, year: int, month: int, seed: int) -> str:
        """Write the state COG per ``docs/abm-output-contract.md`` §1.

        Band 0 = density (mosquitoes / K_MAX ∈ [0, 1]).
        Band 1 = suitability (1.0 for cells with an active patch, else 0.0).
        The file is COG-compatible (tiled, deflate, 128x128 blocks) and
        carries a sidecar JSON next to the ``.tif``.
        """
        h, w = self.aoi.cells_per_side()
        density = self._density_grid(h, w)
        suitability = self._suitability_grid(h, w)
        assert density.shape == (h, w) and suitability.shape == (h, w)
        assert density.dtype == np.float32 and suitability.dtype == np.float32

        transform = from_bounds(*self.aoi.bbox, w, h)
        profile = {
            "driver": "GTiff",
            "dtype": "float32",
            "count": 2,
            "height": h,
            "width": w,
            "crs": self.aoi.crs,
            "transform": transform,
            "nodata": NODATA_SENTINEL,
            "tiled": True,
            "compress": "deflate",
            "blockxsize": 128,
            "blockysize": 128,
        }
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(density, 1)
            dst.write(suitability, 2)
            dst.set_band_description(1, STATE_BAND_NAMES[0])
            dst.set_band_description(2, STATE_BAND_NAMES[1])

        sidecar = {
            "crs": self.aoi.crs,
            "transform": [float(x) for x in transform[:6]],
            "aoi_slug": self.aoi.slug,
            "scale": self.aoi.scale.value,
            "year": int(year),
            "month": int(month),
            "seed": int(seed),
            "generator_version": GENERATOR_VERSION,
            "abm_params_hash": "sha256:pending",
            "contract_version": CONTRACT_VERSION,
            "band_names": list(STATE_BAND_NAMES),
            "nodata": NODATA_SENTINEL,
            "shape": [2, int(h), int(w)],
            "k_max": int(self.K_MAX),
        }
        if path.endswith(".tif"):
            sidecar_path = path[:-4] + ".json"
        else:
            sidecar_path = path + ".json"
        with open(sidecar_path, "w") as fp:
            json.dump(sidecar, fp, indent=2)
        return path


# -- type keys for the scheduler shim ----------------------------------------
# We use dedicated marker classes so larva and adult MosquitoAgents do not
# collide on the shim's dict key (both are ``MosquitoAgent`` instances).

class _LarvaSentinel:
    pass


class _AdultSentinel:
    pass


_LARVA_KEY: type = _LarvaSentinel
_ADULT_KEY: type = _AdultSentinel

# Re-export for tests and downstream callers.
__all__ = ["AnophelesABM", "CONTRACT_VERSION", "GENERATOR_VERSION"]
