"""Agent module for the M1.5 ABM thin slice.

M1.5 splits the M1.4 agent set into two layers:

* **HabitatPatch** (Mesa-Geo ``GeoAgent``) — owned by the
  ``CoordinatorModel``; stored in ``mesa_geo.GeoSpace``.
* **Mosquito agents** (M1.4) — moved to the Polars-backed
  ``MosquitoSubmodel`` as rows in a DataFrame. There is no Python
  ``MosquitoAgent`` class any more; the population is a single
  ``polars.DataFrame`` (``MosquitoSubmodel.df``).

This module re-exports the pieces the rest of the package needs.
"""
from __future__ import annotations

from .habitat import HabitatPatch, HabitatType

#: Re-export HabitatPatch (Mesa-Geo) for callers that still want to
#: reference the agent class directly. The Polars-backed mosquito
#: population lives in ``mal_ghana_sim.abm.mosquito_submodel``.
__all__ = ["HabitatPatch", "HabitatType"]
