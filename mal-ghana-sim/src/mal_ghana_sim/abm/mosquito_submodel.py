"""MosquitoSubmodel — Polars-backed mosquito population (M1.5).

This is the **submodel half** of the M1.5 refactor. The coordinator
(Mesa-Geo) holds the habitat patches and the climate, and exchanges a
per-day ``pl.DataFrame`` with this submodel on every step. The submodel
stores its entire population as rows in a Polars DataFrame — vectorised
SIMD joins, filters, and group_bys replace the per-agent Python loop
that the old ``Mesa-Geo + Mesa`` model ran.

Why a plain ``mesa.Model`` and not ``mesa_frames.Model``?
--------------------------------------------------------
The M1.5 refactor was originally specified against
``mesa-frames>=0.1``. The only PyPI release is ``mesa-frames==0.1.0a0``
(status: Alpha), which has a hard pin on ``numpy~=1.26``. That conflicts
with the project's ``numpy>=2.5.0`` (required by ``torch>=2.12``,
``rioxarray``, and the rest of the geospatial stack). The
``projectmesa/mesa-frames`` main branch has a beartype runtime-dep
problem (``from mesa_frames.types_ import ... pd.DataFrame`` without
importing pandas first), so it does not import cleanly. We therefore
use ``mesa.Model`` as the host and store the agent population in a
``polars.DataFrame`` directly — which is exactly what ``AgentSetPolars``
does internally, minus the masking/select convenience API we don't need.

Public API
----------
``MosquitoSubmodel.__init__(model, n_patches, k_per_patch=1000,
init_frac=0.3, seed=42)`` — construct and seed.
``MosquitoSubmodel.step(day, patch_state_df)`` — advance one day.
``MosquitoSubmodel.density_by_patch()`` — ``{patch_id: count}`` pl.DataFrame.
``MosquitoSubmodel.total_agents()`` — population total.

Lifecycle
---------
The submodel is created once by the facade ``AnophelesABM`` and reused
across the 30-day rollout. The DataFrame is mutated in place (Polars
``DataFrame.with_columns``, ``filter``, etc. all return new objects,
so we reassign ``self.df`` to keep the latest frame).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import mesa
import numpy as np
import polars as pl
import rasterio
from rasterio.transform import from_bounds

if TYPE_CHECKING:
    from datetime import date


#: Polars schema for the mosquito DataFrame. Stable across the rollout.
#: ``patch_id`` is the join key with the coordinator; ``unique_id`` is a
#: row identifier (so per-row operations can target individual agents if
#: we ever need to).
MOSQUITO_SCHEMA: dict[str, pl.DataType] = {
    "unique_id": pl.Int64,
    "patch_id": pl.Int64,
    "row": pl.Int32,
    "col": pl.Int32,
    "stage": pl.Categorical,  # "larva" or "adult"
    "lon": pl.Float32,
    "lat": pl.Float32,
    "eip_progress": pl.Float32,
    "stage_age": pl.Int32,
}

#: Per-day larva -> adult transition rate (temperature-modulated).
#: Thin slice: 18-32 C active range, capped at 1.0.
_PUPATE_BASE_C: float = 18.0
_PUPATE_RANGE_C: float = 14.0

#: EIP (extrinsic incubation period) base temperature in C.
#: daily_gd = max(0, T - EIP_BASE_C). EIP completes at >= 110 GD.
EIP_BASE_C: float = 16.0
EIP_THRESHOLD_GD: float = 110.0

#: Per-day adult dispersal probability.
ADULT_DISPERSE_PROB: float = 0.2
#: Dispersal kernel sigma (m), for ``An. gambiae`` s.s. rural.
ADULT_DISPERSE_SIGMA_M: float = 1000.0
#: Dispersal cap (m).
ADULT_DISPERSE_MAX_M: float = 2000.0

#: Per-patch per-day birth rate (probability of laying one egg batch).
#: Thin slice: each active patch gets ``binomial(K, BIRTH_RATE)`` new
#: larvae per step, which is a small stochastic sample that bounds
#: the population growth around the initial seeded count. The M1.5
#: perf budget (60s for 30k patches + 9M agents on a 16-core Hetzner)
#: assumes the population stays near its initial size; a higher
#: birth rate blows up to 30M agents and overshoots the budget.
BIRTH_RATE: float = 0.005

#: Metres per degree latitude (used to convert dispersal offsets back to
#: degrees). Longitude is converted at the patch's latitude.
_METRES_PER_DEG_LAT: float = 111_320.0


def _lon_lat_offset_m(
    rng: np.random.Generator,
    lon: np.ndarray,
    lat: np.ndarray,
    sigma_m: float,
    max_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (dlon, dlat) arrays of Gaussian offsets in degrees.

    The kernel is isotropic in metres, clipped to ``max_m`` (the rural
    ``An. gambiae`` s.s. 2 km cap). The longitude offset is divided by
    ``cos(lat)`` so the *ground* distance is correct at the patch's
    latitude.
    """
    dx = rng.normal(0.0, sigma_m, size=lon.shape)
    dy = rng.normal(0.0, sigma_m, size=lat.shape)
    dist = np.sqrt(dx * dx + dy * dy)
    over = dist > max_m
    if np.any(over):
        scale = (max_m / np.where(over, dist, 1.0))
        dx = np.where(over, dx * scale, dx)
        dy = np.where(over, dy * scale, dy)
    lat_rad = np.deg2rad(lat)
    m_per_deg_lon = _METRES_PER_DEG_LAT * np.cos(lat_rad)
    dlon = dx / m_per_deg_lon
    dlat = dy / _METRES_PER_DEG_LAT
    return dlon.astype(np.float32), dlat.astype(np.float32)


class MosquitoSubmodel(mesa.Model):
    """Polars-backed mosquito population, one row per agent.

    The submodel is a thin Mesa host around a ``polars.DataFrame`` of
    agents. Every operation that touches the population (mortality,
    growth, EIP, dispersal, birth) is a vectorised Polars / numpy
    expression; there are no per-agent Python loops.

    Determinism
    -----------
    Stochastic draws go through ``self._rng`` (numpy ``Generator``)
    re-seeded from ``seed`` at construction. Two ``MosquitoSubmodel``
    instances with the same seed and the same ``step()`` call sequence
    produce identical populations.
    """

    def __init__(
        self,
        model: mesa.Model | None,
        n_patches: int,
        *,
        k_per_patch: int = 1000,
        init_frac: float = 0.3,
        seed: int = 42,
    ) -> None:
        super().__init__()
        self.n_patches = int(n_patches)
        self.k_per_patch = int(k_per_patch)
        self.init_frac = float(init_frac)
        self._rng = np.random.default_rng(int(seed))
        # Seed 30% of K larvae at each patch. We assign round-robin
        # patch_ids (one row per agent) so the join with patch_state
        # is direct.
        self.df = self._seed_population()

    # -- seeding -------------------------------------------------------------

    def _seed_population(self) -> pl.DataFrame:
        """Seed ``n_patches * k_per_patch * init_frac`` larvae at construction.

        All seeded agents start as larvae at their patch's centroid
        (lon/lat 0, 0 — the coordinator's ``aggregate_density`` only
        reads ``patch_id`` for the per-cell count, not lon/lat; the
        seeded lon/lat is a placeholder overwritten on the first
        dispersal step).
        """
        n = int(round(self.n_patches * self.k_per_patch * self.init_frac))
        if n <= 0:
            return pl.DataFrame(schema=MOSQUITO_SCHEMA)
        # Round-robin patch assignment so each patch gets the same
        # number of larvae. Patch 0..n_patches-1 each get floor(n/n_patches)
        # agents, then the first (n mod n_patches) patches get one more.
        base, rem = divmod(n, self.n_patches) if self.n_patches else (0, 0)
        per_patch = np.full(self.n_patches, base, dtype=np.int64)
        if rem:
            per_patch[:rem] += 1
        patch_ids = np.repeat(np.arange(self.n_patches, dtype=np.int64), per_patch)
        # Rows / cols are placeholders; the coordinator's
        # ``to_dataframe()`` provides the (row, col) per patch.
        rows = np.zeros(n, dtype=np.int32)
        cols = np.zeros(n, dtype=np.int32)
        uids = np.arange(n, dtype=np.int64)
        return pl.DataFrame(
            {
                "unique_id": uids,
                "patch_id": patch_ids,
                "row": rows,
                "col": cols,
                "stage": pl.Series(["larva"] * n, dtype=pl.Categorical),
                "lon": np.zeros(n, dtype=np.float32),
                "lat": np.zeros(n, dtype=np.float32),
                "eip_progress": np.zeros(n, dtype=np.float32),
                "stage_age": np.zeros(n, dtype=np.int32),
            },
            schema=MOSQUITO_SCHEMA,
        )

    # -- per-day step --------------------------------------------------------

    def step(self) -> None:
        """No-op override of ``mesa.Model.step``.

        The submodel's per-day advance is :meth:`advance_day`, which
        takes the patch-state DataFrame as an argument. The facade
        ``AnophelesABM`` calls ``advance_day`` directly; we keep
        ``step`` as a no-op so the submodel is still a valid ``mesa.Model``
        and can be driven by a generic Mesa scheduler if needed.
        """
        return None

    def advance_day(self, day: "date | int", patch_state_df: pl.DataFrame) -> None:
        """Advance the population by one day.

        Per-day order, matching the spec:
            1. Larva mortality at inactive patches.
            2. Larva growth: age + EIP accumulation at active patches.
            3. EIP completion: larva -> adult.
            4. Adult dispersal: 20% chance per day, 2 km cap.
            5. Birth: spawn new larvae at active patches.
        """
        self._larva_mortality_inactive(patch_state_df)
        self._larva_growth(patch_state_df)
        self._larva_to_adult()
        self._adult_dispersal()
        self._birth(patch_state_df)

    # -- per-day operations --------------------------------------------------

    def _larva_mortality_inactive(self, patch_state_df: pl.DataFrame) -> None:
        """Remove larvae whose patch is currently inactive.

        Vectorised: filter patch_state to inactive patches, then
        ``is_in`` on the mosquito DataFrame's ``patch_id`` column.
        Polars broadcasts the join without a Python loop.
        """
        if self.df.is_empty():
            return
        inactive_ids = patch_state_df.filter(~pl.col("activated"))["patch_id"]
        if inactive_ids.is_empty():
            return
        # Materialise the inactive ids as a Python set for the ``is_in``
        # filter; the set lookup is O(1) and avoids a Polars join for
        # the common case (sparse inactivation).
        inactive_set = set(inactive_ids.to_list())
        # ``is_in`` on a Python list of ints compiles to a hash join
        # inside Polars. Cheap on millions of rows.
        self.df = self.df.filter(
            ~(pl.col("patch_id").is_in(list(inactive_set)) & (pl.col("stage") == "larva"))
        )

    def _larva_growth(self, patch_state_df: pl.DataFrame) -> None:
        """Age larvae at active patches; accumulate EIP.

        ``stage_age += 1`` for every larva at an active patch. EIP is
        accumulated as ``eip_progress += max(0, temp_d - EIP_BASE_C)``
        — same rule as the old per-agent loop in
        ``eip.accumulate_eip``.
        """
        if self.df.is_empty():
            return
        active = patch_state_df.filter(pl.col("activated")).select(
            ["patch_id", "temp_d"]
        )
        if active.is_empty():
            return
        # Join brings ``temp_d`` onto each larva; we update only the
        # active-patch larvae. Polars handles the join in a single pass.
        joined = self.df.join(active, on="patch_id", how="left")
        is_larva = pl.col("stage") == "larva"
        is_active = pl.col("temp_d").is_not_null()
        new_age = pl.when(is_larva & is_active).then(pl.col("stage_age") + 1).otherwise(
            pl.col("stage_age")
        )
        daily_gd = pl.max_horizontal(
            pl.lit(0.0),
            pl.col("temp_d").fill_null(0.0) - pl.lit(EIP_BASE_C),
        )
        new_eip = pl.when(is_larva & is_active).then(
            pl.col("eip_progress") + daily_gd
        ).otherwise(pl.col("eip_progress"))
        # Drop the helper ``temp_d`` column before reassignment.
        self.df = joined.with_columns([new_age.alias("stage_age"), new_eip.alias("eip_progress")]).drop(
            "temp_d"
        )

    def _larva_to_adult(self) -> None:
        """Promote larvae with ``eip_progress >= EIP_THRESHOLD_GD`` to adults.

        The thin slice collapses pupation + emergence into the EIP
        threshold: a larva that has accumulated enough GD is an adult.
        (In M2+ the pupation step is split out.)
        """
        if self.df.is_empty():
            return
        threshold = float(EIP_THRESHOLD_GD)
        self.df = self.df.with_columns(
            pl.when(
                (pl.col("stage") == "larva") & (pl.col("eip_progress") >= threshold)
            )
            .then(pl.lit("adult", dtype=pl.Categorical))
            .otherwise(pl.col("stage"))
            .alias("stage")
        )

    def _adult_dispersal(self) -> None:
        """Move ~20% of adults by a clipped Gaussian in metres.

        The kernel is isotropic in metres; the result is converted back
        to (dlon, dlat) at the agent's current latitude and added to
        its lon/lat. The stochastic draw uses ``self._rng`` so the
        trajectory is reproducible.
        """
        if self.df.is_empty():
            return
        # Select adult rows in a numpy array for the kernel; we then
        # fold the result back into Polars.
        adults = self.df.filter(pl.col("stage") == "adult")
        if adults.is_empty():
            return
        lon = adults["lon"].to_numpy()
        lat = adults["lat"].to_numpy()
        uids = adults["unique_id"].to_numpy()
        # Draw which adults actually disperse (20%).
        n = lon.shape[0]
        mask = self._rng.random(n) < ADULT_DISPERSE_PROB
        if not np.any(mask):
            return
        dlon, dlat = _lon_lat_offset_m(
            self._rng, lon[mask], lat[mask],
            ADULT_DISPERSE_SIGMA_M, ADULT_DISPERSE_MAX_M,
        )
        new_lon = lon[mask] + dlon
        new_lat = lat[mask] + dlat
        # Build a small DataFrame with the updates and join back on
        # unique_id. This is the only way to do in-place updates on a
        # subset of rows in Polars.
        updates = pl.DataFrame(
            {
                "unique_id": uids[mask],
                "_new_lon": new_lon,
                "_new_lat": new_lat,
            },
            schema={
                "unique_id": pl.Int64,
                "_new_lon": pl.Float32,
                "_new_lat": pl.Float32,
            },
        )
        joined = self.df.join(updates, on="unique_id", how="left")
        self.df = joined.with_columns(
            [
                pl.when(pl.col("_new_lon").is_not_null())
                .then(pl.col("_new_lon"))
                .otherwise(pl.col("lon"))
                .alias("lon"),
                pl.when(pl.col("_new_lat").is_not_null())
                .then(pl.col("_new_lat"))
                .otherwise(pl.col("lat"))
                .alias("lat"),
            ]
        ).drop(["_new_lon", "_new_lat"])

    def _birth(self, patch_state_df: pl.DataFrame) -> None:
        """Spawn new larvae at active patches (stochastic, capped).

        The thin slice uses a Bernoulli sample with probability
        :data:`BIRTH_RATE` per patch per step. This bounds the
        population growth around the initial seeded count and keeps
        the per-step operations O(N) where N is the current
        population, not O(N_patches * K).

        For a 30k-patch / 9M-agent rollout this caps the birth at
        ~150k new agents per step (binomial(30k * 1000, 0.005) ≈ 150k),
        so the population grows to ~13M after 30 days — within the
        perf budget for the target Hetzner machine.

        M2 combined, C1: the new larvae's ``lon/lat`` is set to the
        patch's own ``(cx, cy)`` (read from the patch-state DataFrame
        via the env callable) so that ``adult_density_by_cell`` (which
        uses each adult's post-dispersal ``lon/lat`` snapped to the
        AOI grid) reports the adults at the **patch cell**, not at
        ``(0, 0)`` (the placeholder used in the M1.5 thin slice).
        Without this, adults that emerged from a water cell but did
        not disperse would still snap to ``(0, 0)`` and the M2
        suitability band would not see the cell of the dynamic
        patch.
        """
        active = patch_state_df.filter(pl.col("activated")).select(
            ["patch_id", "row", "col"]
        )
        if active.is_empty():
            return
        n_active = int(active.height)
        if n_active == 0:
            return
        # Stochastic per-patch birth: ``binomial(K, p)`` per patch.
        # Vectorised via numpy — the draw is per active patch, not
        # per agent.
        capacity = int(self.k_per_patch)
        n_per_patch = self._rng.binomial(capacity, BIRTH_RATE, size=n_active)
        total_birth = int(n_per_patch.sum())
        if total_birth <= 0:
            return
        new_uids = self._next_uid_range(total_birth)
        active_ids = active["patch_id"].to_numpy()
        new_patch_ids = np.repeat(active_ids, n_per_patch)
        # Repeat the per-patch (row, col) for each newborn larva.
        new_rows = np.repeat(active["row"].to_numpy(), n_per_patch)
        new_cols = np.repeat(active["col"].to_numpy(), n_per_patch)
        # Look up the (lon, lat) for each active patch from the
        # model's env via the model's own AOI transform. We use a
        # model reference if available; otherwise fall back to (0, 0)
        # — the M1.5 placeholder, which is what ``_seed_population``
        # also uses when no AOI is provided.
        from rasterio.transform import xy as transform_xy
        aoi = getattr(getattr(self, "model", None), "aoi", None)
        coord_transform = None
        if aoi is not None:
            try:
                h, w = aoi.cells_per_side()
                coord_transform = from_bounds(*aoi.bbox, w, h)
            except Exception:
                coord_transform = None
        # The active patch's lon/lat is the centre of its (row, col)
        # cell on the AOI grid.
        lons = np.zeros(total_birth, dtype=np.float32)
        lats = np.zeros(total_birth, dtype=np.float32)
        if coord_transform is not None:
            for i in range(n_active):
                if n_per_patch[i] == 0:
                    continue
                lon_i, lat_i = transform_xy(
                    coord_transform, int(new_rows[i]), int(new_cols[i]),
                )
                start = int(np.concatenate([[0], n_per_patch[:i]]).sum())
                lons[start:start + int(n_per_patch[i])] = float(lon_i)
                lats[start:start + int(n_per_patch[i])] = float(lat_i)
        new_df = pl.DataFrame(
            {
                "unique_id": new_uids,
                "patch_id": new_patch_ids,
                "row": new_rows.astype(np.int32),
                "col": new_cols.astype(np.int32),
                "stage": pl.Series(["larva"] * total_birth, dtype=pl.Categorical),
                "lon": lons,
                "lat": lats,
                "eip_progress": np.zeros(total_birth, dtype=np.float32),
                "stage_age": np.zeros(total_birth, dtype=np.int32),
            },
            schema=MOSQUITO_SCHEMA,
        )
        self.df = pl.concat([self.df, new_df], how="diagonal_relaxed")

    def _next_uid_range(self, n: int) -> np.ndarray:
        """Allocate ``n`` new unique_ids contiguously from the next free slot.

        ``self.df`` is the current population; ``self._next_uid`` is the
        next free integer. ``unique_id`` is unique across the entire
        lifetime of the submodel (so a larva that later becomes an
        adult keeps its id).
        """
        if not hasattr(self, "_next_uid"):
            if self.df.is_empty():
                self._next_uid = 0
            else:
                self._next_uid = int(self.df["unique_id"].max()) + 1
        start = self._next_uid
        self._next_uid = start + int(n)
        return np.arange(start, start + n, dtype=np.int64)

    # -- queries -------------------------------------------------------------

    def density_by_patch(self) -> pl.DataFrame:
        """Return a DataFrame with one row per patch and a ``count`` column.

        Patches with zero agents are absent (the caller can fill in
        zeros if needed via ``join(how='left')`` on the patch_state).
        """
        if self.df.is_empty():
            return pl.DataFrame(
                {"patch_id": [], "count": []},
                schema={"patch_id": pl.Int64, "count": pl.UInt32},
            )
        return (
            self.df.group_by("patch_id")
            .len()
            .rename({"len": "count"})
            .with_columns(pl.col("count").cast(pl.UInt32))
            .sort("patch_id")
        )

    def adult_density_by_patch(self) -> pl.DataFrame:
        """Return a DataFrame with one row per patch and an ``n_adults`` column.

        Patches with zero adults are absent. The coordinator's
        ``suitability_grid`` calls this and joins the result onto
        ``_cell_lookup`` to build the per-cell adult-density band of
        the state COG (the M2 suitability band: ``n_adults / K_MAX``).

        Why this exists
        ---------------
        The M1.4 suitability band was ``1.0 for cells with an active
        patch, else 0.0``. That misses female adults that dispersed
        from a water cell into a dry cell — and the 20 larval sites in
        ``data/ghana_idit/occurrence.txt`` are dry cells within
        dispersal range of water. Reporting adult density per cell
        means dry cells with a non-zero suitability from dispersed
        adults are picked up, restoring the M2 validation's ability
        to produce a non-NaN AUC.
        """
        if self.df.is_empty():
            return pl.DataFrame(
                {"patch_id": [], "n_adults": []},
                schema={"patch_id": pl.Int64, "n_adults": pl.UInt32},
            )
        return (
            self.df.filter(pl.col("stage") == "adult")
            .group_by("patch_id")
            .len()
            .rename({"len": "n_adults"})
            .with_columns(pl.col("n_adults").cast(pl.UInt32))
            .sort("patch_id")
        )

    def adult_density_by_cell(self, aoi) -> pl.DataFrame:
        """Return a DataFrame with one row per occupied cell and an ``n_adults`` column.

        Uses each adult's **current** ``lon/lat`` (i.e. after today's
        ``_adult_dispersal`` step) and snaps it onto the AOI grid via
        ``rasterio.transform.rowcol`` + ``from_bounds``. Pairs of
        ``(row, col)`` with zero adults are absent. The coordinator's
        ``suitability_grid`` calls this (instead of
        ``adult_density_by_patch``) so the suitability band reflects
        where the adult is *after* dispersal, not where it was born.

        The 20 larval sites in ``data/ghana_idit/occurrence.txt`` sit
        in dry cells within dispersal range of water — adults that
        emerged from a water cell and dispersed into a dry site cell
        are picked up by this method, but were missed by the v1
        ``adult_density_by_patch`` (which grouped by ``patch_id`` and
        so counted them in the water cell instead).

        Args:
            aoi: the AOI used to build the grid transform.

        Returns:
            ``pl.DataFrame`` with columns ``row`` (Int32), ``col``
            (Int32), ``n_adults`` (UInt32). Sorted by ``(row, col)``.
        """
        h, w = aoi.cells_per_side()
        transform = from_bounds(*aoi.bbox, w, h)
        if self.df.is_empty():
            return pl.DataFrame(
                {"row": [], "col": [], "n_adults": []},
                schema={"row": pl.Int32, "col": pl.Int32, "n_adults": pl.UInt32},
            )
        adults = self.df.filter(pl.col("stage") == "adult")
        if adults.is_empty():
            return pl.DataFrame(
                {"row": [], "col": [], "n_adults": []},
                schema={"row": pl.Int32, "col": pl.Int32, "n_adults": pl.UInt32},
            )
        lon = adults["lon"].to_numpy()
        lat = adults["lat"].to_numpy()
        # Snap lon/lat → (row, col) using the AOI transform. ``rowcol``
        # returns generator-like tuples; we materialise and clamp to
        # the grid bounds (an adult can disperse slightly outside the
        # AOI).
        rows, cols = rasterio.transform.rowcol(transform, lon, lat)
        rows_arr = np.clip(np.asarray(list(rows), dtype=np.int64), 0, int(h) - 1)
        cols_arr = np.clip(np.asarray(list(cols), dtype=np.int64), 0, int(w) - 1)
        return (
            pl.DataFrame({"row": rows_arr, "col": cols_arr})
            .group_by(["row", "col"])
            .len()
            .rename({"len": "n_adults"})
            .with_columns(pl.col("n_adults").cast(pl.UInt32))
            .sort(["row", "col"])
        )

    def total_agents(self) -> int:
        """Current population (larvae + adults)."""
        return int(len(self.df))


__all__ = [
    "MosquitoSubmodel",
    "MOSQUITO_SCHEMA",
    "EIP_BASE_C",
    "EIP_THRESHOLD_GD",
    "ADULT_DISPERSE_PROB",
    "ADULT_DISPERSE_SIGMA_M",
    "ADULT_DISPERSE_MAX_M",
]
