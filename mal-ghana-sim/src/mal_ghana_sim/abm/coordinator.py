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

Public API
----------
``CoordinatorModel(aoi, env, habitat_gdf, *, seed, start_date)``
    Build a coordinator with a 4-band env dict, a habitat gpkg, and
    the model seed.
``coordinator.activate_patches(day)``
    Update ``patch.activated`` from climate for ``day``.
``coordinator.to_dataframe() -> pl.DataFrame``
    Return the current per-patch state as a Polars DataFrame (the
    join key the submodel expects).
``coordinator.aggregate_density(mosquito_df, k_max) -> np.ndarray``
    Group ``mosquito_df`` by ``patch_id``, join the cell lookup, and
    return the (H, W) density grid normalised by ``k_max``.
``coordinator.suitability_grid() -> np.ndarray``
    Return the (H, W) suitability grid (1.0 for cells with an active
    patch, else 0.0).
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

        One row per patch, columns match :data:`patch_state.PATCH_STATE_SCHEMA`.
        The submodel joins on ``patch_id`` to compute per-patch
        mortality, growth, EIP, etc.
        """
        states: list[PatchState] = []
        for idx, patch in enumerate(self.habitat_engine.patches):
            cell = self._cell_lookup.get(idx)
            if cell is None:
                # Skip patches whose cell is not in the AOI grid.
                # The cell lookup is built in ``__init__`` and falls
                # back to None if the patch geometry is empty or
                # outside the AOI; the M1.4 model would still seed
                # larvae at those patches. We follow the M1.4 rule:
                # default to (0, 0) so the agent gets a cell.
                cell = (0, 0)
            row, col = cell
            # water_frac is read per patch from the static grid; the
            # grid accessor returns 0.5 for unknown keys, which is
            # the same default the M1.4 climate facade uses.
            water_frac = float(
                self.climate.get_water_frac(
                    patch.geometry.x if patch.geometry is not None else 0.0,
                    patch.geometry.y if patch.geometry is not None else 0.0,
                )
            )
            states.append(
                patch.to_patch_state(
                    idx, row, col, water_frac=water_frac,
                )
            )
        return patch_states_to_dataframe(states)

    # -- density aggregation ------------------------------------------------

    def aggregate_density(
        self,
        mosquito_df: pl.DataFrame,
        k_max: int | None = None,
    ) -> np.ndarray:
        """Build the (H, W) density grid from the submodel's DataFrame.

        Steps (all Polars, no Python loop over agents):
          1. ``mosquito_df.group_by('patch_id').len()`` → per-patch count.
          2. Left-join with ``self._cell_lookup`` keyed on ``patch_id``
             (materialised as a Polars DataFrame once per call).
          3. ``np.bincount`` over the linear cell index → grid.
          4. Clip to [0, 1] after dividing by ``k_max``.
        """
        h, w = self.aoi.cells_per_side()
        if k_max is None:
            k_max = int(self.K_MAX)
        # Materialise the cell lookup as a Polars DataFrame. The
        # per-patch id is the index in ``self.habitat_engine.patches``.
        if not self._cell_lookup:
            return np.zeros((h, w), dtype=np.float32)
        cell_df = pl.DataFrame(
            {
                "patch_id": list(self._cell_lookup.keys()),
                "row": [v[0] for v in self._cell_lookup.values()],
                "col": [v[1] for v in self._cell_lookup.values()],
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

    def suitability_grid(self) -> np.ndarray:
        """Build the (H, W) suitability grid (1.0 for cells with an active patch)."""
        h, w = self.aoi.cells_per_side()
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
