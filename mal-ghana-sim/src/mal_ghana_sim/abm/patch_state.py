"""PatchState — the per-day interface between the coordinator and the submodel.

The coordinator (Mesa-Geo ``CoordinatorModel``) materialises
``HabitatPatch`` agents and, on each step, computes the per-patch state
that the Polars-backed submodel needs to advance the mosquito life cycle.
That state is a small record (one row per patch) that travels between the
two models as a ``polars.DataFrame`` — the format the submodel can join
on in a single vectorised pass.

Why a dataclass and not just a Polars DataFrame?  Two reasons:

1. The schema lives in one place (``PatchState`` + ``PATCH_STATE_SCHEMA``)
   so the coordinator can build the DataFrame by row-append in pure
   Python and the submodel can validate at import time.
2. ``to_patch_state()`` on ``HabitatPatch`` returns a ``PatchState`` —
   a clean object that can be unit-tested without a Mesa context.

The DataFrame is the wire format; the dataclass is the in-Python handle.
"""
from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class PatchState:
    """Per-day state of one habitat patch, exchanged with the submodel.

    Attributes
    ----------
    patch_id : int
        Stable identifier for the patch (its position in
        ``habitat_engine.patches``).
    row, col : int
        Cell index on the AOI grid (for ``aggregate_density``).
    activated : bool
        True iff the patch is currently active (rain_24h > RAIN_THRESHOLD_MM
        for ``PLUVIAL_POOL``).
    rain_d : float
        Daily rainfall (mm) at the patch's centroid.
    temp_d : float
        Daily water temperature (C) at the patch's centroid.
    water_frac : float
        Fraction of the patch's cell covered by open water, ∈ [0, 1].
    """

    patch_id: int
    row: int
    col: int
    activated: bool
    rain_d: float
    temp_d: float
    water_frac: float


#: Polars schema for the per-day patch-state DataFrame exchanged between
#: the coordinator and the submodel. Both sides import this to make sure
#: their join keys line up.
PATCH_STATE_SCHEMA: dict[str, pl.DataType] = {
    "patch_id": pl.Int64,
    "row": pl.Int32,
    "col": pl.Int32,
    "activated": pl.Boolean,
    "rain_d": pl.Float32,
    "temp_d": pl.Float32,
    "water_frac": pl.Float32,
}


def patch_states_to_dataframe(states: list[PatchState]) -> pl.DataFrame:
    """Build a Polars DataFrame from a list of ``PatchState``.

    The schema is fixed (see :data:`PATCH_STATE_SCHEMA`) so the submodel
    can ``join`` on ``patch_id`` without a runtime schema check.
    """
    if not states:
        return pl.DataFrame(schema=PATCH_STATE_SCHEMA)
    return pl.DataFrame(
        {
            "patch_id": [s.patch_id for s in states],
            "row": [s.row for s in states],
            "col": [s.col for s in states],
            "activated": [s.activated for s in states],
            "rain_d": [s.rain_d for s in states],
            "temp_d": [s.temp_d for s in states],
            "water_frac": [s.water_frac for s in states],
        },
        schema=PATCH_STATE_SCHEMA,
    )


__all__ = ["PatchState", "PATCH_STATE_SCHEMA", "patch_states_to_dataframe"]
