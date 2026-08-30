"""D11: Aquatic stage structure.

The cohort log's ``n_alive`` counts ADULTS only — larval stages live
in the aquatic JSONs (``*_dayNNN_aquatic.json`` with ``by_stage``
egg/larva/pupa). This scorer validates the stage distribution of the
aquatic population against stage-duration data:

- Bayoh & Lindsay 2003 (papers/anopheles-dynamics/, constant 25 C):
  egg ~1.1 d, each larval instar 2-3 d (4 instars = 8-12 d), pupa
  ~1.2 d -> expected larva fraction = 8-12 / 10.3-14.3 = 0.78-0.84,
  pupa fraction = 1.2 / 10.3-14.3 = 0.08-0.12.
- Ouedraogo et al. 2024 (semi-field, Burkina Faso, 24.5-28.5 C):
  L1 -> pupation 11.87 d — consistent stage ratios.
- Depinay et al. 2004: total egg-to-adult 11-13 d at 25 C.

Bands (widened for temperature-driven ratio drift between 18-30 C):
larva fraction [0.65, 0.90]; pupa fraction [0.02, 0.15].
Score = mean of both sub-scores. Fallback: final summary aquatic JSON
when per-day files are absent.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .base import (
    Scorer,
    ScorerResult,
    find_aquatic_day_files,
    find_final_aquatic,
)

LARVA_BAND = (0.65, 0.90)
PUPA_BAND = (0.02, 0.15)


def _structure_from(data: dict[str, Any]) -> tuple[float, float] | None:
    stage = data.get("by_stage")
    total = data.get("total_aquatic", 0)
    if not isinstance(stage, dict) or not total:
        return None
    larva = float(stage.get("larva", 0.0))
    pupa = float(stage.get("pupa", 0.0))
    return larva / total, pupa / total


class AquaticStructureScorer(Scorer):
    name = "D11_aquatic_structure"
    kind = "composite"
    weight = 1.0
    description = "Larval/pupal share of aquatic population vs stage-duration data (Bayoh 2003)"
    min_score = 0.7
    hard_floor = 0.3

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        target = f"larva {LARVA_BAND[0]}-{LARVA_BAND[1]}, pupa {PUPA_BAND[0]}-{PUPA_BAND[1]}"
        daily = find_aquatic_day_files(run_dir)
        sources = daily[-30:] if daily else []
        final = find_final_aquatic(run_dir)
        if not sources and final is not None:
            sources = [final]
        if not sources:
            return ScorerResult.skipped(
                "no aquatic JSONs (*_dayNNN_aquatic.json / *_aquatic.json)",
                target=target,
            )
        larva_fracs: list[float] = []
        pupa_fracs: list[float] = []
        for path in sources:
            try:
                data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            pair = _structure_from(data)
            if pair is not None:
                larva_fracs.append(pair[0])
                pupa_fracs.append(pair[1])
        if not larva_fracs:
            return ScorerResult.skipped(
                "aquatic JSONs lack by_stage/total_aquatic",
                target=target,
            )
        larva_frac = sum(larva_fracs) / len(larva_fracs)
        pupa_frac = sum(pupa_fracs) / len(pupa_fracs)

        # stage-duration expectation (Bayoh & Lindsay 2003, 25 C):
        # larva 0.78-0.84, pupa 0.08-0.12; bands widened for 18-30 C drift
        lo, hi = LARVA_BAND
        if lo <= larva_frac <= hi:
            larva_ok = 1.0
        elif larva_frac < lo:
            larva_ok = max(0.0, larva_frac / lo)
        else:
            larva_ok = max(0.0, (1.0 - larva_frac) / (1.0 - hi))

        plo, phi = PUPA_BAND
        if plo <= pupa_frac <= phi:
            pupa_ok = 1.0
        else:
            edge = plo if pupa_frac < plo else phi
            pupa_ok = max(0.0, math.exp(-((pupa_frac - edge) / 0.08) ** 2))

        score = (larva_ok + pupa_ok) / 2.0
        return ScorerResult(
            score=round(score, 4),
            value=round(larva_frac, 4),
            target=target,
            diagnostics={
                "larva_frac": round(larva_frac, 4),
                "pupa_frac": round(pupa_frac, 4),
                "n_files": len(larva_fracs),
            },
            passed=score >= self.min_score,
        )
