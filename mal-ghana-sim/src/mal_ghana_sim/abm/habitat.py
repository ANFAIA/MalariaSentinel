"""Habitat patches for the M1 ABM thin slice.

M1 implements **one** habitat subtype: ``PLUVIAL_POOL`` (TWI-driven
depression). All other Hardy 2013 subtypes are ``[M7+]`` per
``docs/abm-mesa-geo-adaptation.md`` §3.

Activation: a ``PLUVIAL_POOL`` is activated when ``rain_24h`` exceeds
``RAIN_THRESHOLD_MM`` (15 mm in v1). Production is the Beverton-Holt-like
density-dependent survival curve carried over from the M1 casablanca:
``survival = 0.95 * K / (K + 0.05 * max(0, N - K))``.
"""
from __future__ import annotations

from enum import Enum

from mesa_geo.geoagent import GeoAgent


class HabitatType(str, Enum):
    """Habitat subtype enum. M1 only uses ``PLUVIAL_POOL``; the rest are inert."""

    PLUVIAL_POOL = "pluvial_pool"  # only one used in M1


class HabitatPatch(GeoAgent):
    """Larval habitat patch (Mesa-Geo v0.9.3 ``GeoAgent`` subclass).

    M1 implements a single type (``PLUVIAL_POOL``). The patch carries
    per-patch state (activation, water temperature, capacity) and exposes
    a deterministic mortality / production API used by ``AnophelesABM``.
    """

    RAIN_THRESHOLD_MM: float = 15.0

    def __init__(
        self,
        model,
        geometry,
        crs,
        *,
        K: int = 1000,
        twi_value: float = 0.0,
    ) -> None:
        # Mesa-Geo v0.9.3 GeoAgent is (model, geometry, crs) — no unique_id.
        super().__init__(model, geometry, crs)
        self.hab_type: HabitatType = HabitatType.PLUVIAL_POOL
        self.K: int = min(int(K), int(model.K_MAX))
        self.activated: bool = False
        self.rain_24h: float = 0.0
        self.water_temp_c: float = 25.0
        self.twi_value: float = float(twi_value)
        self.predator_pressure: float = 0.0

    def step(self) -> None:
        """Mesa-Geo agent step. The M1 scheduler calls this once per day.

        For v1 the activation is computed elsewhere (driven by the model's
        climate facade calling ``activate(rain, water_temp)``); ``step``
        is a no-op kept for the scheduler shim's uniform contract.
        """
        return None

    def activate(self, rain_24h: float, water_temp_c: float) -> None:
        """Activate/deactivate the patch based on daily rain and water temperature.

        ``PLUVIAL_POOL`` activation rule (M1 v1): ``rain_24h > RAIN_THRESHOLD_MM``.
        """
        self.rain_24h = float(rain_24h)
        self.water_temp_c = float(water_temp_c)
        self.activated = bool(rain_24h > self.RAIN_THRESHOLD_MM)

    def mortality(self, N: int, *, density_dep: bool = True) -> int:
        """Return the number of larvae that die this step.

        With ``density_dep=False`` returns 0 (no density-dependent deaths;
        useful for ablation / unit tests). With ``density_dep=True`` applies
        the Beverton-Holt-like survival curve:

            survival = 0.95 * K / (K + 0.05 * max(0, N - K))

        and returns ``N - int(round(survival * N))``.
        """
        N = int(N)
        if N <= 0:
            return 0
        if not density_dep:
            return 0
        K = max(1, int(self.K))
        excess = max(0, N - K)
        survival = 0.95 * K / (K + 0.05 * excess)
        survival = max(0.0, min(1.0, survival))
        dead = N - int(round(survival * N))
        return max(0, min(N, dead))

    def produce_adults(self, N: int, model) -> int:
        """Return the number of adults produced from ``N`` larvae this step.

        M1 collapses egg + pupa: larvae that survive to ``stage_age_days`` at
        or above the pupation threshold (a function of water temperature) are
        converted 1:1 into adults. For the thin slice we use a simple
        temperature-modulated probability:

            p_pupate = clip((water_temp_c - 18) / 14, 0, 1)  # 18..32 C active

        Adults that emerge are deposited on the model via
        ``model._deposit_adult(patch, count)`` (caller's responsibility).
        This method is pure (no side effects on the model) so it is testable.
        """
        N = int(N)
        if N <= 0 or not self.activated:
            return 0
        temp = float(self.water_temp_c)
        p_pupate = max(0.0, min(1.0, (temp - 18.0) / 14.0))
        # Stochastic pupation: 1 trial per larva, weighted by p_pupate.
        # Uses the model's numpy RNG so the run is reproducible.
        if hasattr(model, "rng") and model.rng is not None:
            survivors = int(model.rng.binomial(N, p_pupate))
        else:
            survivors = int(round(N * p_pupate))
        return max(0, min(N, survivors))
