"""DEPRECATED shim — constants migrate to mal-core/config/model_constants.yaml.

DELETED at the constants-yaml migration: NOTHING lives here any more.
This module raises for every attribute: new code must read
``mal_core.habitat.config`` (CONFIG singleton) — ``mal-core/config/
model_constants.yaml`` is the single source of shared py⇄C++ model
constants.

The engine-side k_ref (species.k_ref, ind·km⁻²·d⁻¹) and the py-diagnostic
K_REF_DIAG_PER_KM2 are different concepts; the diagnostic
constant lives in ``mal_core.habitat.capacity``.
"""
from __future__ import annotations


def __getattr__(name: str):
    """Reject every attribute access: the constants moved to the model configuration.

    Raises AttributeError pointing at ``mal_core.habitat.config`` and
    ``mal-core/config/model_constants.yaml``.
    """
    raise AttributeError(
        f"mal_core.habitat.constants.{name} was removed: constants live "
        "in mal-core/config/model_constants.yaml — read them via "
        "mal_core.habitat.config (plan constants-yaml paso 8). See "
        "mal_core.habitat.capacity.K_REF_DIAG_PER_KM2 for the py "
        "diagnostic constant renamed from K_REF_DAILY_PER_KM2.")
