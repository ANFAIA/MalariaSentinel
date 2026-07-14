"""CoordinatorModel — the Mesa-Geo half of the M1.5 ABM (M1.5).

The coordinator owns the **spatial layer**: the ``mesa_geo.GeoSpace``,
the ``HabitatPatch`` agents, and the climate lookups. Per step it
builds a per-patch ``PatchState`` ``polars.DataFrame`` and hands it to
the ``MosquitoSubmodel`` for the vectorised day advance. It then
turns the submodel's per-patch density into the (H, W) density grid
for the state COG.

The coordinator is the only piece that knows about ``mesa_geo``,
shapely, rasterio, and the AOI grid. The submodel only knows about
Polars, numpy, and the patch_id join key.

M2 combined (JRC GSW + adult density by cell + dynamic patches):
* **JRC GSW** is now the water layer (``build_env`` calls
  ``load_jrc_gsw_water_frac`` instead of WorldCover); the habitat
  patches gpkg is unchanged in shape.
* **C1**: ``coordinator.suitability_grid`` accepts an optional
  ``submodel`` kwarg; if both ``mosquito_df`` and ``submodel`` are
  passed, the suitability band is the per-cell adult density computed
  from each adult's **post-dispersal** ``lon/lat`` (snapped via
  ``rasterio.transform.rowcol``). This replaces the v1 path that
  grouped by ``patch_id`` and so missed adults that dispersed into
  dry cells.
* **C2**: ``coordinator.to_dataframe`` and
  ``coordinator.aggregate_density`` operate on the **union** of
  pre-existing patches (loaded from the gpkg) and dynamic patches
  (cells where ``TWI > 8 AND water_frac > 0 AND rain_24h > 15mm``
  today). Dynamic patches are assigned stable ``patch_id``s on first
  emergence and retained in the registry (site fidelity); they
  reappear in the per-day patch-state DataFrame automatically if
  the rule holds again on a later day.

Public API
----------
``CoordinatorModel(aoi, env, habitat_gdf, *, seed, start_date)``
    Build a coordinator with a 4-band env dict, a habitat gpkg, and
    the model seed.
``coordinator.activate_patches(day)``
    Update ``patch.activated`` from climate for ``day``.
``coordinator.to_dataframe() -> pl.DataFrame``
    Return the current per-patch state as a Polars DataFrame (the
    join key the submodel expects). Includes dynamic patches
    (cells where the PLUVIAL_POOL rule holds today).
``coordinator.aggregate_density(mosquito_df, k_max) -> np.ndarray``
    Group ``mosquito_df`` by ``patch_id``, join the cell lookup
    (covering pre-existing + dynamic patches), and return the (H, W)
    density grid normalised by ``k_max``.
``coordinator.suitability_grid(mosquito_df=None, k_max=None, submodel=None) -> np.ndarray``
    Return the (H, W) suitability grid. v1 (no ``mosquito_df``/no
    ``submodel``): 1.0 for cells with an active patch, else 0.0
    (backward-compat fallback). v2 (M2 combined, C1): per-cell adult
    density from each adult's post-dispersal ``lon/lat``, normalised
    by ``k_max``.
``coordinator.write_state_cog(path, density, suitability, *, year, month, seed)``
    Write the 2-band state COG and its JSON sidecar (per
    ``docs/abm-output-contract.md`` §1). The density / suitability
    grids are computed by the facade and passed in so the coordinator
    has no dependency on the submodel.
"""
from __future__ import annotations

import json
from datetime import date as _date
from typing import TYPE_CHECKING

import mesa
import mesa_geo
import numpy as np
import polars as pl
import rasterio
from rasterio.transform import from_bounds

from .climate import ClimateEngine
from .habitat_engine import HabitatEngine
from .patch_state import PatchState, patch_states_to_dataframe
from .scheduler import RandomActivationByTypeShim

if TYPE_CHECKING:
    import geopandas as gpd

    from .mosquito_submodel import MosquitoSubmodel


CONTRACT_VERSION: str = "1.0"
GENERATOR_VERSION: str = "m1.5-mesa-frames+polars"
NODATA_SENTINEL: float = -9999.0
STATE_BAND_NAMES: tuple[str, ...] = ("density", "suitability")


class CoordinatorModel(mesa.Model):
    """Mesa-Geo coordinator for the M1.5 thin-slice ABM.

    The coordinator's per-day contract with the submodel is:

    1. ``coordinator.activate_patches(day)``
    2. ``patch_state = coordinator.to_dataframe()``
    3. ``submodel.advance_day(day, patch_state)``
    4. ``density = coordinator.aggregate_density(submodel.df, k_max)``
    5. (later) ``coordinator.write_state_cog(path, density, suitability, ...)``

    The facade ``AnophelesABM`` orchestrates steps 1-4 and exposes
    step 5 as the public ``snapshot`` method.
    """

    K_MAX: int = 1000

    def __init__(
        self,
        aoi,
        env: dict,
        habitat_patches_gdf: "gpd.GeoDataFrame",
        *,
        seed: int = 42,
        start_date: _date | None = None,
    ) -> None:
        super().__init__()
        self.aoi = aoi
        self.env = env
        self.current_date: _date | None = start_date
        # Per-Mesa-3.5.1 convention: numpy ``Generator`` keyed off ``seed``.
        # Both the Mesa model ``self.random`` and our shim use this.
        self.rng = np.random.default_rng(int(seed))
        # Scheduler is still the M1.4 shim — the Mesa-Geo
        # ``HabitatPatch.step()`` contract needs a per-agent tick even
        # though the patch's actual work is done in
        # ``activate_patches``. Keeping the shim avoids changes to
        # downstream code that introspects ``model.schedule``.
        self.schedule = RandomActivationByTypeShim(self)
        self.climate = ClimateEngine(env)
        # Materialise the habitat patches via the existing engine
        # (same code path as the M1.4 model; preserves the gpkg
        # reading + row/col lookup logic).
        self.habitat_engine = HabitatEngine(aoi, habitat_patches_gdf)
        self.habitat_engine.materialise(self)
        # Mesa-Geo GeoSpace — kept as a CRS holder. The patches are
        # registered with the scheduler shim, not with the GeoSpace;
        # the spatial index is only used by the (now removed)
        # per-patch agent logic. We keep the GeoSpace as a no-op CRS
        # holder.
        self.geospace = mesa_geo.GeoSpace(crs="EPSG:4326")
        # Pre-build the patch_id -> (row, col) lookup once; the
        # per-day ``to_dataframe()`` reuses it.
        self._cell_lookup: dict[int, tuple[int, int]] = {}
        self._build_cell_lookup()
        # M2 combined, C2: dynamic patch emergence. The per-day
        # patch-state DataFrame is the **union** of pre-existing
        # patches (loaded from the gpkg) and cells where the
        # PLUVIAL_POOL rule holds today. Dynamic patches are
        # assigned stable ``patch_id``s on first emergence and kept
        # in the registry (site fidelity); a cell that drops out of
        # the active set is not removed (so a future activation
        # reuses the same ``patch_id``).
        self._dynamic_patch_registry: dict[tuple[int, int], int] = {}
        self._next_dynamic_patch_id: int = len(self.habitat_engine.patches)

    # -- cell-index helpers --------------------------------------------------

    def _build_cell_lookup(self) -> None:
        """Map each patch to its ``(row, col)`` cell on the AOI grid.

        Reads the ``row``/``col`` columns from the gpkg if present
        (the M1.3b ``build_env`` writes them); otherwise derives them
        from the patch's geometry and the AOI's transform.
        """
        h, w = self.aoi.cells_per_side()
        transform = from_bounds(*self.aoi.bbox, w, h)
        for idx, patch in enumerate(self.habitat_engine.patches):
            row = col = None
            try:
                row_series = self.habitat_engine.gdf.iloc[idx].get("row")
                col_series = self.habitat_engine.gdf.iloc[idx].get("col")
                if row_series is not None and col_series is not None:
                    row = int(row_series)
                    col = int(col_series)
            except (TypeError, ValueError):
                row = col = None
            if row is None or col is None:
                geom = patch.geometry
                if geom is not None and not geom.is_empty:
                    from rasterio.transform import rowcol
                    try:
                        r, c = rowcol(transform, geom.x, geom.y)
                        row, col = int(r), int(c)
                    except Exception:
                        row = col = None
            if row is None or col is None:
                continue
            self._cell_lookup[idx] = (row, col)

    # -- per-day: activation + patch-state DataFrame ------------------------

    def activate_patches(self, day: _date) -> None:
        """Update ``patch.activated`` from climate for ``day``.

        Each patch reads its own ``(cx, cy)`` from its geometry and
        queries ``ClimateEngine`` with the day's value. For a thin
        slice on 30k patches this is a few ms.
        """
        for patch in self.habitat_engine.patches:
            if patch.geometry is None or patch.geometry.is_empty:
                continue
            cx, cy = patch.geometry.x, patch.geometry.y
            rain = self.climate.get_rain_daily(day, cx, cy)
            water_temp = self.climate.get_water_temp_c(day, cx, cy)
            patch.activate(rain, water_temp)

    def to_dataframe(self) -> pl.DataFrame:
        """Return the current per-patch state as a Polars DataFrame.

        One row per active cell today (pre-existing + dynamic), columns
        match :data:`patch_state.PATCH_STATE_SCHEMA`. The submodel
        joins on ``patch_id`` to compute per-patch mortality, growth,
        EIP, etc.

        M2 combined, C2: the per-day patch-state DataFrame is the
        **union** of pre-existing patches (loaded from the gpkg) and
        cells where the PLUVIAL_POOL rule holds today (``TWI > 8 AND
        water_frac > 0 AND rain_24h > 15mm``). Dynamic patches are
        assigned stable ``patch_id``s on first emergence and retained
        in the registry (site fidelity); a cell that drops out of the
        active set is not removed (so a future activation reuses the
        same ``patch_id``).
        """
        if self.current_date is None:
            day = _date(2000, 1, 1)
        else:
            day = self.current_date
        self._refresh_dynamic_patch_registry(day)
        cells = self.dynamic_patches_today(day)
        states: list[PatchState] = []
        for cell in cells:
            row, col = cell
            pid = self._dynamic_patch_registry.get(cell, -1)
            if pid < 0:
                continue
            # Build the per-cell climate values. Pre-existing patches
            # use the patch's own (cx, cy); dynamic patches derive
            # lon/lat from the cell coordinates via the AOI
            # transform.
            from rasterio.transform import xy as transform_xy
            if pid < len(self.habitat_engine.patches):
                patch = self.habitat_engine.patches[pid]
                cx = patch.geometry.x if patch.geometry is not None else 0.0
                cy = patch.geometry.y if patch.geometry is not None else 0.0
                water_frac = float(self.climate.get_water_frac(cx, cy))
            else:
                # Dynamic patch — derive (cx, cy) from cell coords.
                transform = from_bounds(
                    *self.aoi.bbox, *self.aoi.cells_per_side(),
                )
                cx, cy = transform_xy(transform, row, col)
                water_frac = float(self.climate.get_water_frac(cx, cy))
            rain = float(self.climate.get_rain_daily(day, cx, cy))
            water_temp = float(self.climate.get_water_temp_c(day, cx, cy))
            # Build a PatchState with activated=True (we already
            # filtered by the rule) and the assigned patch_id.
            states.append(PatchState(
                patch_id=int(pid),
                row=int(row),
                col=int(col),
                activated=True,
                rain_d=float(rain),
                temp_d=float(water_temp),
                water_frac=float(water_frac),
            ))
        return patch_states_to_dataframe(states)

    def dynamic_patches_today(self, day) -> list[tuple[int, int]]:
        """Return the (row, col) of every cell that is a habitat patch today.

        Combines two sources:
          (a) Pre-existing patches from ``self.habitat_engine.patches``
              that are ``activated`` by today's climate.
          (b) Cells in the AOI grid where the PLUVIAL_POOL rule holds
              today: ``TWI > 8 AND water_frac > 0 AND rain_24h > 15mm``.

        The union is returned as a sorted list. Pre-existing patches
        are kept in the registry even if they stop satisfying the rule
        (site fidelity); the submodel only sees the cells that satisfy
        the rule *today* (so an inactive pre-existing patch produces
        no larvae until it reactivates).
        """
        h, w = self.aoi.cells_per_side()
        rain_grid = self.climate.rain_daily_grid(day, h, w)
        water_frac_grid = self.climate.water_frac_grid(h, w)
        twi_grid = self.env.get("twi")
        if twi_grid is None:
            twi_grid = np.zeros((h, w), dtype=np.float32)
        else:
            twi_grid = np.asarray(twi_grid, dtype=np.float32)
            if twi_grid.shape != (h, w):
                if twi_grid.shape == (h * w,):
                    twi_grid = twi_grid.reshape(h, w)
                else:
                    twi_grid = np.broadcast_to(
                        twi_grid.mean(), (h, w),
                    ).astype(np.float32)
        active_mask = (twi_grid > 8.0) & (water_frac_grid > 0.0) & (rain_grid > 15.0)
        dynamic_rows, dynamic_cols = np.where(active_mask)
        dynamic_cells = list(zip(dynamic_rows.tolist(), dynamic_cols.tolist()))
        preexisting = [
            self._cell_lookup[idx]
            for idx, patch in enumerate(self.habitat_engine.patches)
            if patch.activated and idx in self._cell_lookup
        ]
        all_cells = set(preexisting) | set(dynamic_cells)
        return sorted(all_cells)

    def _refresh_dynamic_patch_registry(self, day) -> None:
        """Assign a stable patch_id to every (row, col) that becomes active today.

        Pre-existing cells keep their original ``patch_id`` from
        ``_cell_lookup``. New cells get a fresh ``patch_id`` starting
        from ``len(self.habitat_engine.patches)``. Cells that drop out
        of today's active set are NOT removed from the registry (site
        fidelity) — they simply don't appear in the per-day patch-state
        DataFrame and thus don't produce larvae, but they reappear
        automatically if the rule holds again on a later day.
        """
        cells = self.dynamic_patches_today(day)
        for cell in cells:
            if cell in self._cell_lookup.values():
                # Pre-existing patch — find its patch_id.
                for pid, c in self._cell_lookup.items():
                    if c == cell:
                        self._dynamic_patch_registry[cell] = pid
                        break
            elif cell not in self._dynamic_patch_registry:
                # New dynamic cell.
                self._dynamic_patch_registry[cell] = int(self._next_dynamic_patch_id)
                self._next_dynamic_patch_id += 1

    # -- density aggregation ------------------------------------------------

    def aggregate_density(
        self,
        mosquito_df: pl.DataFrame,
        k_max: int | None = None,
    ) -> np.ndarray:
        """Build the (H, W) density grid from the submodel's DataFrame.

        Steps (all Polars, no Python loop over agents):
          1. ``mosquito_df.group_by('patch_id').len()`` → per-patch count.
          2. Left-join with the cell lookup keyed on ``patch_id``
             (covering pre-existing + dynamic patches via
             ``self._dynamic_patch_registry``).
          3. ``np.bincount`` over the linear cell index → grid.
          4. Clip to [0, 1] after dividing by ``k_max``.
        """
        h, w = self.aoi.cells_per_side()
        if k_max is None:
            k_max = int(self.K_MAX)
        # Build a (patch_id, row, col) lookup covering both pre-existing
        # and dynamic patches. M2 combined, C2: dynamic patches have
        # ``patch_id >= len(self.habitat_engine.patches)`` and are kept
        # in ``_dynamic_patch_registry`` for site fidelity.
        rows_map: dict[int, int] = {
            pid: r for pid, (r, _) in self._cell_lookup.items()
        }
        cols_map: dict[int, int] = {
            pid: c for pid, (_, c) in self._cell_lookup.items()
        }
        for (r, c), pid in self._dynamic_patch_registry.items():
            rows_map[pid] = r
            cols_map[pid] = c
        if not rows_map:
            return np.zeros((h, w), dtype=np.float32)
        cell_df = pl.DataFrame(
            {
                "patch_id": list(rows_map.keys()),
                "row": list(rows_map.values()),
                "col": list(cols_map.values()),
            },
            schema={"patch_id": pl.Int64, "row": pl.Int32, "col": pl.Int32},
        )
        if mosquito_df.is_empty():
            counts = cell_df.with_columns(pl.lit(0).cast(pl.UInt32).alias("count"))
        else:
            counts = (
                mosquito_df.group_by("patch_id").len().rename({"len": "count"})
            )
            counts = cell_df.join(counts, on="patch_id", how="left").with_columns(
                pl.col("count").fill_null(0).cast(pl.UInt32)
            )
        # Now ``counts`` has (patch_id, row, col, count) with one row
        # per patch. Build the (H, W) grid via ``np.bincount`` on the
        # linear cell index.
        rows = counts["row"].to_numpy()
        cols = counts["col"].to_numpy()
        cnts = counts["count"].to_numpy()
        linear = rows.astype(np.int64) * int(w) + cols.astype(np.int64)
        flat = np.bincount(linear, weights=cnts.astype(np.float64), minlength=h * w)
        grid = flat[: h * w].reshape(h, w).astype(np.float32)
        # Normalise by K_MAX and clip.
        if k_max > 0:
            grid = np.clip(grid / float(k_max), 0.0, 1.0)
        return grid

    def suitability_grid(
        self,
        mosquito_df: pl.DataFrame | None = None,
        k_max: int | None = None,
        submodel: "MosquitoSubmodel | None" = None,
    ) -> np.ndarray:
        """Build the (H, W) suitability grid.

        **M2 semantics (default, used by the facade ``AnophelesABM.snapshot``):**
        the suitability band is the **adult mosquito density per cell** —
        the number of adult agents at the cell, divided by ``k_max`` and
        clipped to [0, 1]. The M2 fix uses each adult's **post-dispersal**
        ``lon/lat`` (snapped to the AOI grid via
        ``rasterio.transform.rowcol``) so the band reflects where the
        adult is *after* today's ``_adult_dispersal`` step, not its
        origin patch. This is critical: a female adult that emerged
        from a water cell and dispersed into a dry cell (the 20 larval
        sites in ``data/ghana_idit/occurrence.txt`` are dry cells
        within ``An. gambiae`` s.s. dispersal range of water) must
        show up as ``suitability > 0`` at the **site cell**, not at
        the origin patch cell.

        Two code paths:

        * **v1 (backward-compat, ``mosquito_df is None``)**: 1.0 for
          cells with an active patch, else 0.0. Used by tests that
          inspect the activation diagnostic. The M2 facade never
          reaches this path — ``AnophelesABM.snapshot`` always passes
          both ``mosquito_df`` and ``submodel``.
        * **v2 (M2 combined, C1, ``mosquito_df is not None and
          submodel is not None``)**: adult density by cell from
          ``submodel.adult_density_by_cell(self.aoi)``, rasterised via
          ``np.bincount`` on the linear cell index, normalised by
          ``k_max``, clipped to [0, 1].

        Args:
            mosquito_df: the submodel's per-day mosquito DataFrame. If
                None, the v1 binary map is returned (backward compat).
            k_max: normalisation constant for the density grid. Defaults
                to ``self.K_MAX``. Must be > 0 if ``mosquito_df`` and
                ``submodel`` are provided.
            submodel: the M2 submodel instance. If provided together
                with ``mosquito_df``, the per-cell adult density is
                computed from the adult's post-dispersal ``lon/lat``
                (the M2 semantics). Required to enable the v2 path.

        Returns:
            A ``(H, W)`` float32 array with values in [0, 1].
        """
        h, w = self.aoi.cells_per_side()
        if mosquito_df is None or submodel is None:
            # v1 path: 1.0 for cells with an active patch.
            grid = np.zeros((h, w), dtype=np.float32)
            for idx, patch in enumerate(self.habitat_engine.patches):
                if not patch.activated:
                    continue
                cell = self._cell_lookup.get(idx)
                if cell is None:
                    continue
                row, col = cell
                if 0 <= row < h and 0 <= col < w:
                    grid[row, col] = 1.0
            return grid
        # v2 path (M2 combined, C1): adult density by cell (lon/lat
        # post-dispersal), normalised by k_max, clipped to [0, 1].
        if k_max is None:
            k_max = int(self.K_MAX)
        adult_cell_df = submodel.adult_density_by_cell(self.aoi)
        grid = np.zeros((h, w), dtype=np.float32)
        if adult_cell_df.is_empty():
            return grid
        rows = adult_cell_df["row"].to_numpy().astype(np.int64)
        cols = adult_cell_df["col"].to_numpy().astype(np.int64)
        cnts = adult_cell_df["n_adults"].to_numpy().astype(np.float64)
        linear = rows * int(w) + cols
        flat = np.bincount(linear, weights=cnts, minlength=h * w)
        grid = flat[: h * w].reshape(h, w).astype(np.float32)
        if k_max > 0:
            grid = np.clip(grid / float(k_max), 0.0, 1.0)
        return grid

    # -- snapshot ------------------------------------------------------------

    def write_state_cog(
        self,
        path: str,
        density: np.ndarray,
        suitability: np.ndarray,
        *,
        year: int,
        month: int,
        seed: int,
    ) -> str:
        """Write the state COG and sidecar JSON (M1.4 contract, unchanged).

        The density / suitability grids are passed in so the
        coordinator has no dependency on the submodel. Band 0 is
        density (mosquitoes / K_MAX ∈ [0, 1]); band 1 is
        suitability (1.0 for cells with an active patch, else 0.0).
        The file is COG-compatible (tiled, deflate, 128x128 blocks)
        and carries a sidecar JSON next to the ``.tif``.
        """
        h, w = self.aoi.cells_per_side()
        assert density.shape == (h, w) and suitability.shape == (h, w), (
            f"density/suitability must be (H={h}, W={w}); "
            f"got {density.shape} and {suitability.shape}"
        )
        assert density.dtype == np.float32 and suitability.dtype == np.float32, (
            f"density/suitability must be float32; "
            f"got {density.dtype} and {suitability.dtype}"
        )

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


__all__ = ["CoordinatorModel", "CONTRACT_VERSION", "GENERATOR_VERSION"]
