"""Scheduler shim for Mesa 3.5.1.

Mesa 3.5.1 removed ``mesa.time.RandomActivationByType`` (the ``mesa.time``
module is now a thin wrapper around ``Event`` / ``EventList`` /
``Schedule``). The M1 ABM needs the surface area of the old scheduler
(``add`` / ``remove`` / ``step`` / ``counts`` / ``get``) keyed by agent
type. ``RandomActivationByTypeShim`` reproduces it locally, shuffling
per-type lists with a stdlib ``random.Random`` re-seeded from
``model.rng`` (numpy's ``Generator``) for reproducibility.

Why re-seed per call? ``model.rng`` is a numpy ``Generator``; the
shim's shuffle is stdlib ``random.shuffle`` (in-place). Bridging once
per ``step`` keeps the deterministic stream while still mixing the
agent order so the run is not deterministic-by-construction.
"""
from __future__ import annotations

import random
from collections.abc import Iterable


class RandomActivationByTypeShim:
    """Local replacement for ``mesa.time.RandomActivationByType``.

    Parameters
    ----------
    model : mesa.Model
        The owning model. The shim reads ``model.rng`` (numpy Generator)
        once per ``step`` to re-seed a stdlib ``random.Random`` for
        each per-type shuffle.

    Notes
    -----
    * ``agents_by_type`` is keyed by **agent class** (``type``), not by
      string label. The M1 model registers ``HabitatPatch``,
      ``MosquitoAgent`` (larva) and ``MosquitoAgent`` (adult) under
      distinct keys via ``add(agent, type_key=...)``.
    * ``step()`` iterates over a *snapshot* of the keys, so removing
      an agent from one type does not skip the next type.
    """

    def __init__(self, model) -> None:
        self.model = model
        self.agents_by_type: dict[type, list] = {}

    def add(self, agent, type_key: type | None = None) -> None:
        """Register ``agent`` under ``type_key`` (defaults to ``type(agent)``)."""
        key = type_key if type_key is not None else type(agent)
        bucket = self.agents_by_type.setdefault(key, [])
        bucket.append(agent)

    def remove(self, agent, type_key: type | None = None) -> None:
        """Remove ``agent`` from its bucket. No-op if absent."""
        key = type_key if type_key is not None else type(agent)
        bucket = self.agents_by_type.get(key)
        if not bucket:
            return
        try:
            bucket.remove(agent)
        except ValueError:
            pass

    def step(self) -> None:
        """Shuffle each type's agents (seeded from ``model.rng``) and call ``.step()``."""
        # Snapshot the keys so removals during iteration do not skip types.
        type_keys: Iterable[type] = list(self.agents_by_type.keys())
        for type_key in type_keys:
            agent_list = self.agents_by_type.get(type_key, [])
            if not agent_list:
                continue
            shuffled = list(agent_list)
            seed = self._seed_for_step(type_key)
            rng = random.Random(seed)
            rng.shuffle(shuffled)
            for agent in shuffled:
                # Agents may have been removed by a prior step's actions;
                # check membership to avoid double-stepping.
                if agent in self.agents_by_type.get(type_key, []):
                    agent.step()

    def _seed_for_step(self, type_key: type) -> int:
        """Derive a per-call seed from ``model.rng`` (numpy Generator)."""
        model_rng = getattr(self.model, "rng", None)
        if model_rng is None:
            return 0
        # numpy Generator.integers(low, high) is exclusive at the high end.
        return int(model_rng.integers(0, 2**31 - 1))

    def counts(self) -> dict[type, int]:
        """Return ``{type_key: len(agents)}`` for all registered types."""
        return {k: len(v) for k, v in self.agents_by_type.items()}

    def get(self, type_key: type, index: int = 0):
        """Return the ``index``-th agent of ``type_key`` (default 0)."""
        bucket = self.agents_by_type.get(type_key, [])
        if not bucket:
            return None
        if index < 0:
            index = len(bucket) + index
        if not (0 <= index < len(bucket)):
            return None
        return bucket[index]
