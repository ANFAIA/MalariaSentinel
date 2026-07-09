"""M1 Mesa-Geo ABM thin slice for MalariaSentinel Centinela.

Implements the M1 thin slice per ``docs/abm-mesa-geo-adaptation.md`` and
``docs/abm-output-contract.md`` v1.0:
  * 1 species (*An. gambiae* s.s. rural)
  * 1 habitat subtype (``PLUVIAL_POOL``, TWI-driven)
  * 2 stages (larva + adult; egg + pupa collapsed)
  * Stochastic grid on ``EPSG:4326``
  * Monthly snapshot output (state COG, 2 bands: density + suitability)
"""
from __future__ import annotations

__version__ = "0.1.0"
