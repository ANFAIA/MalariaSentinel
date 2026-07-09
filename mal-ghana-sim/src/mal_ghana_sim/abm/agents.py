"""Mosquito agent for the M1 ABM thin slice (2 stages: larva + adult).

M1 collapses egg + pupa into the larva-to-adult transition. The adult
carries a tiny state machine (host-seeking / resting / sugar-feeding)
and an EIP tracker for *P. falciparum* sporozoite development.

Local dispersal is a clipped Gaussian in metres around the patch's
longitude/latitude. Wind-borne long-range dispersal is ``[M7+]``.
"""
from __future__ import annotations

import mesa_geo

from .habitat import HabitatPatch


class MosquitoAgent(mesa_geo.GeoAgent):
    """Individual mosquito agent (M1: 2 stages, larva + adult).

    ``stage`` is one of ``{"larva", "adult"}``. ``stage_age_days`` is the
    days spent in the current stage; transition larva->adult happens via
    ``HabitatPatch.produce_adults`` (a per-patch batch event, not a
    per-agent event in the thin slice).

    ``hbi`` is the human-biting index (anthropophily); *An. gambiae* s.s.
    defaults to 0.95 (highly anthropophilic). EIP accumulates via
    ``abm.eip.accumulate_eip``; the mosquito becomes infective at
    ``eip_progress >= 110 GD``.
    """

    def __init__(
        self,
        model,
        geometry,
        crs,
        *,
        sex: str = "female",
        hbi: float = 0.95,
    ) -> None:
        # Mesa-Geo v0.9.3 GeoAgent is (model, geometry, crs) — no unique_id.
        super().__init__(model, geometry, crs)
        self.stage: str = "larva"
        self.stage_age_days: int = 0
        self.sex: str = sex
        self.hbi: float = float(hbi)
        self.eip_progress: float = 0.0
        self.sugar_energy: float = 1.0
        self.host_seeking_state: str = "resting"
        # Reference to the patch that produced the agent (None for synthetic seeds).
        self.origin_patch: HabitatPatch | None = None

    def step(self) -> None:
        """Mesa-Geo agent step. Called once per day by the scheduler shim.

        The thin slice keeps the state machine intentionally minimal:
        the larva counts its age; the adult ticks the EIP (if any) and
        decays sugar energy. Real state transitions are driven by
        ``AnophelesABM._step_habitats()`` and ``_deposit_adult()``.
        """
        self.stage_age_days += 1
        if self.stage == "adult":
            # Sugar energy decays at 1/7 per day (fully depleted in ~7 days).
            self.sugar_energy = max(0.0, self.sugar_energy - 1.0 / 7.0)
        return None

    def _local_disperse(
        self,
        rng,
        sigma_m: float = 1000.0,
        max_distance_m: float = 2000.0,
    ) -> None:
        """Stochastic local dispersal (clipped Gaussian in metres).

        Translates ``self.geometry`` by a sample from
        ``Normal(0, sigma_m)`` in each axis, clipped to ``max_distance_m``.
        Wind-borne long-range dispersal is ``[M7+]``; this is the *An. gambiae*
        rural short-range kernel.
        """
        if self.geometry is None or getattr(self.geometry, "is_empty", False):
            return
        try:
            dx = float(rng.normal(0.0, float(sigma_m)))
            dy = float(rng.normal(0.0, float(sigma_m)))
        except AttributeError:
            dx = float(rng.normalvariate(0.0, float(sigma_m)))
            dy = float(rng.normalvariate(0.0, float(sigma_m)))
        dist = (dx * dx + dy * dy) ** 0.5
        if dist > float(max_distance_m):
            scale = float(max_distance_m) / dist
            dx *= scale
            dy *= scale
        from shapely.affinity import translate  # local import: heavy
        self.geometry = translate(self.geometry, xoff=dx, yoff=dy)
