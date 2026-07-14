"""AnophelesABM facade — backward-compatible wrapper for the M1.5 ABM.

The M1.5 refactor splits the M1.4 ``AnophelesABM`` into two layers:

* ``CoordinatorModel`` (Mesa-Geo) — owns the spatial layer: the
  ``mesa_geo.GeoSpace``, ``HabitatPatch`` agents, and the climate
  lookups. It materialises per-patch state into a Polars DataFrame
  once per step.
* ``MosquitoSubmodel`` (Polars-backed ``mesa.Model``) — owns the
  mosquito population. Every per-day operation (mortality, growth,
  EIP, dispersal, birth) is a vectorised Polars expression over the
  mosquito DataFrame.

This module exposes the **same public API** as the M1.4 ``AnophelesABM``
(``__init__``, ``step``, ``snapshot``) so ``run.py`` and
``validate_m2.py`` keep working without changes.

Per-day contract
----------------
``AnophelesABM.step()`` orchestrates one day's advance::

    1. coordinator.activate_patches(day)            # O(P) Mesa-Geo
    2. patch_state = coordinator.to_dataframe()     # O(P) → polars
    3. submodel.advance_day(day, patch_state)       # O(N) vectorised
    4. coordinator.snapshot(...) at month end       # write COG

Where ``P`` is the number of patches (~30k for the regional AOI) and
``N`` is the number of agents (~9M for K=1000, init_frac=0.3).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import mesa
import numpy as np
import polars as pl

from .coordinator import (
    CONTRACT_VERSION,
    GENERATOR_VERSION,
    CoordinatorModel,
)
from .mosquito_submodel import MosquitoSubmodel
from .patch_state import PatchState

if TYPE_CHECKING:
    import geopandas as gpd


# Re-export the contract / generator version constants for any caller
# that previously imported them from ``model``.
__all__ = [
    "AnophelesABM",
    "CoordinatorModel",
    "MosquitoSubmodel",
    "PatchState",
    "CONTRACT_VERSION",
    "GENERATOR_VERSION",
]


class AnophelesABM(mesa.Model):
    """Facade over the M1.5 ``CoordinatorModel`` + ``MosquitoSubmodel``.

    The facade has the same ``__init__``, ``step`` and ``snapshot``
    signatures as the M1.4 ``AnophelesABM``; all the M1.4 fields
    (``aoi``, ``env``, ``current_date``, ``rng``, ``schedule``,
    ``habitat_engine``, ``climate``, ``geospace``, ``_cell_lookup``)
    are exposed as attributes on the coordinator (accessible as
    ``self.coordinator.<attr>`` for backward compat in tests that
    introspect the model).

    Backward-compat shims
    ---------------------
    * ``self.schedule`` — delegated to the coordinator's scheduler
      shim. The M1.4 tests assert on ``model.schedule.agents_by_type``;
      that still works.
    * ``self.rng`` — delegates to the coordinator's numpy
      ``Generator`` (same seed as the submodel's ``_rng``? no — the
      submodel has its own rng; tests that introspect ``model.rng``
      see the coordinator's).
    * ``self.habitat_engine``, ``self.climate``, ``self.geospace`` —
      delegated to the coordinator.
    * ``self._cell_lookup`` — re-exposed as a property that returns
      the coordinator's lookup.
    """

    K_MAX: int = 1000

    def __init__(
        self,
        aoi,
        env: dict,
        habitat_patches_gdf: "gpd.GeoDataFrame",
        *,
        seed: int = 42,
        start_date: date | None = None,
    ) -> None:
        super().__init__()
        # Build the coordinator (spatial layer). The submodel depends
        # on the patch count from the coordinator, so we materialise
        # the patches first and then construct the submodel.
        self.coordinator = CoordinatorModel(
            aoi, env, habitat_patches_gdf,
            seed=int(seed), start_date=start_date,
        )
        n_patches = len(self.coordinator.habitat_engine.patches)
        # M2 combined, C2: an empty gpkg is now allowed. Patches
        # emerge dynamically as cells that satisfy the PLUVIAL_POOL
        # rule today (``TWI > 8 AND water_frac > 0 AND rain_24h >
        # 15mm``); the submodel's population is then driven by those
        # dynamic patches' births. The M1.5 thin slice required >= 1
        # pre-existing patch to seed the submodel; that constraint is
        # relaxed here so the C2 e2e test (no pre-existing patches,
        # one dynamic cell after 15 days) can run.
        self.submodel = MosquitoSubmodel(
            model=self,
            n_patches=n_patches,
            k_per_patch=int(self.K_MAX),
            init_frac=0.3,
            seed=int(seed),
        )
        # Stash for tests + log.
        self.aoi = aoi
        self.env = env
        self.current_date = start_date
        # Re-point ``self.rng`` at the coordinator's numpy Generator
        # so any caller that introspects ``model.rng`` (e.g. the M1.4
        # scheduler shim) sees the same stream the patches use. Mesa
        # 3.5.1's ``__init__`` already set ``self.rng`` to a
        # ``np.random.default_rng(None)`` Generator; we overwrite it
        # with the coordinator's seeded one for reproducibility.
        self.rng = self.coordinator.rng

    # -- backward-compat property shims ------------------------------------

    @property
    def schedule(self):
        return self.coordinator.schedule

    @property
    def habitat_engine(self):
        return self.coordinator.habitat_engine

    @property
    def climate(self):
        return self.coordinator.climate

    @property
    def geospace(self):
        return self.coordinator.geospace

    @property
    def _cell_lookup(self) -> dict:
        # M1.4 stored a ``{patch_idx: linear_cell}`` map; M1.5 stores
        # a ``{patch_idx: (row, col)}`` map. Expose the row/col form
        # for the M1.5 callers; the M1.4 tests that did
        # ``model._cell_lookup[idx]`` and expected an int would now
        # see a tuple. None of the M1.4 tests use ``_cell_lookup``
        # directly — they go through ``model.habitat_engine.patches``
        # and ``model.schedule.agents_by_type``.
        return self.coordinator._cell_lookup

    # -- per-day advance -----------------------------------------------------

    def step(self) -> None:
        """Advance the model by one day (M1.4 contract, unchanged)."""
        if self.current_date is None:
            self.current_date = date(2000, 1, 1)
        # 1. Activate habitat patches from climate.
        self.coordinator.activate_patches(self.current_date)
        # 2. Build the patch-state Polars DataFrame.
        patch_state = self.coordinator.to_dataframe()
        # 3. Advance the mosquito population.
        self.submodel.advance_day(self.current_date, patch_state)
        # 4. Tick the Mesa-Geo scheduler shim so the HabitatPatch
        #    ``step()`` contract is honoured (no-op in M1.5 but kept
        #    for symmetry with the M1.4 scheduler). The submodel
        #    also keeps ``self.step`` as a no-op.
        self.coordinator.schedule.step()
        # 5. Advance the clock.
        self.current_date = self.current_date + timedelta(days=1)

    # -- snapshot ------------------------------------------------------------

    def snapshot(self, path: str, *, year: int, month: int, seed: int) -> str:
        """Write the state COG (M1.4 contract, updated to M2 semantics).

        **M2 change:** band 1 (suitability) is now the per-cell adult
        density (``n_adults / K_MAX``), not the legacy
        "1.0 for cells with an active patch" binary map. The new
        semantics are what the M2 validation needs to produce a
        non-NaN AUC against the 20 larval sites in
        ``data/ghana_idit/occurrence.txt`` — those sites sit in dry
        cells that are within dispersal range of water cells, so
        the adults that dispersed there must show up as
        ``suitability > 0`` at the site cell.

        The per-cell adult density uses each adult's **post-dispersal**
        ``lon/lat`` (snapped to the AOI grid via
        ``rasterio.transform.rowcol``). This is the M2 combined, C1
        fix: the v1 path (``adult_density_by_patch``) grouped by
        ``patch_id`` and so counted an adult at its origin patch's
        cell even after it had dispersed. The v2 path
        (``adult_density_by_cell``) is invoked by
        ``coordinator.suitability_grid`` when both ``mosquito_df`` and
        ``submodel`` are passed.
        """
        # Build the density grid from the submodel's DataFrame.
        density = self.coordinator.aggregate_density(
            self.submodel.df, k_max=int(self.K_MAX),
        )
        # Suitability grid: per-cell adult density / K_MAX, computed
        # from each adult's post-dispersal lon/lat (C1). The submodel
        # kwarg switches the v2 path on in
        # ``coordinator.suitability_grid``.
        suitability = self.coordinator.suitability_grid(
            self.submodel.df, k_max=int(self.K_MAX), submodel=self.submodel,
        )
        return self.coordinator.write_state_cog(
            path, density, suitability,
            year=int(year), month=int(month), seed=int(seed),
        )
