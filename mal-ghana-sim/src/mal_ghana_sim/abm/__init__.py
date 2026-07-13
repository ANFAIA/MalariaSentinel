"""M1.5 Mesa-Geo + Polars ABM thin slice for MalariaSentinel Centinela.

M1.5 splits the M1.4 ABM into two layers:

* **Coordinator** (``CoordinatorModel``, Mesa-Geo) — owns the spatial
  layer: ``mesa_geo.GeoSpace``, ``HabitatPatch`` agents, climate
  lookups. Materialises per-patch state into a Polars DataFrame once
  per step.
* **Submodel** (``MosquitoSubmodel``, Polars-backed ``mesa.Model``) —
  owns the mosquito population. Every per-day operation (mortality,
  growth, EIP, dispersal, birth) is a vectorised Polars expression
  over the population DataFrame.

The ``AnophelesABM`` facade wires the two together and exposes the
same public API as the M1.4 ``AnophelesABM`` (``__init__``, ``step``,
``snapshot``) so ``run.py`` and ``validate_m2.py`` keep working
without changes.

Implements the M1 thin slice per ``docs/abm-mesa-geo-adaptation.md`` and
``docs/abm-output-contract.md`` v1.0:
  * 1 species (*An. gambiae* s.s. rural)
  * 1 habitat subtype (``PLUVIAL_POOL``, TWI-driven)
  * 2 stages (larva + adult; egg + pupa collapsed)
  * Stochastic grid on ``EPSG:4326``
  * Monthly snapshot output (state COG, 2 bands: density + suitability)

M1.5 changes from M1.4:
  * Mosquito population is a ``polars.DataFrame`` (vectorised SIMD).
  * Scales to 10^6+ agents (vs M1.4's ~10^3 Python objects).
  * ``mesa-frames`` is NOT used (see the module docstring in
    ``mosquito_submodel.py`` for the rationale). The architectural
    pattern (coordinator + Polars submodel) is what the
    mesa-frames maintainers recommend; we implement it directly.
"""
from __future__ import annotations

from .coordinator import (
    CONTRACT_VERSION,
    GENERATOR_VERSION,
    CoordinatorModel,
)
from .model import AnophelesABM
from .mosquito_submodel import (
    EIP_BASE_C,
    EIP_THRESHOLD_GD,
    MosquitoSubmodel,
    MOSQUITO_SCHEMA,
)
from .patch_state import PATCH_STATE_SCHEMA, PatchState, patch_states_to_dataframe

__version__ = "0.5.0"  # M1.5

__all__ = [
    "AnophelesABM",
    "CoordinatorModel",
    "MosquitoSubmodel",
    "PatchState",
    "PATCH_STATE_SCHEMA",
    "patch_states_to_dataframe",
    "MOSQUITO_SCHEMA",
    "EIP_BASE_C",
    "EIP_THRESHOLD_GD",
    "CONTRACT_VERSION",
    "GENERATOR_VERSION",
    "__version__",
]
