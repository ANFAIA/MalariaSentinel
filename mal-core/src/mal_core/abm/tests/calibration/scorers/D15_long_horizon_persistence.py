"""D15: Long-horizon population persistence.

Scores whether the ABM population survives for 365 days without extinction.
This scorer catches regressions like the day-90 population crash that no
30-day scorer detects.

Dimensions:
- survival: pop(day=365) >= 30% of peak pop
- no_extinction: pop(day) > 0 for all days [30, 365]
- expansion: cells with adults @ day 365 >= 20% of cells with adults @ day 30
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from scorers.base import Scorer, ScorerResult

_DAY_RE = re.compile(r"_day(\d+)_aquatic\.json$")


def _parse_day(path: Path) -> int | None:
    m = _DAY_RE.search(path.name)
    return int(m.group(1)) if m else None


def _load_aquatic(run_dir: Path) -> dict[int, dict[str, Any]]:
    """Load all *_day*_aquatic.json files, keyed by day number."""
    data: dict[int, dict[str, Any]] = {}
    for p in run_dir.glob("*_day*_aquatic.json"):
        day = _parse_day(p)
        if day is None:
            continue
        try:
            data[day] = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
    return data


def _find_state_cog(run_dir: Path, day: int) -> Path | None:
    pattern = f"*_day{day:03d}.tif"
    matches = sorted(run_dir.glob(pattern))
    return matches[0] if matches else None


def _count_occupied_cells(tif_path: Path, threshold: float = 0.05) -> int:
    """Count cells with density > threshold in band 1 of a state COG."""
    try:
        import numpy as np
        import rasterio
    except ImportError:
        return 0
    try:
        with rasterio.open(tif_path) as ds:
            band = ds.read(1)
        valid = np.isfinite(band) & (band != -9999.0)
        return int((valid & (band > threshold)).sum())
    except Exception:
        return 0


class LongHorizonPersistenceScorer(Scorer):
    @property
    def name(self) -> str:
        return "D15_long_horizon_persistence"

    @property
    def weight(self) -> float:
        return 3.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        aquatic = _load_aquatic(run_dir)
        if not aquatic:
            return ScorerResult(
                score=0.0,
                value=0.0,
                target="pop(day365) >= 30% peak, no extinction, 20% coverage",
                diagnostics={"error": "no aquatic JSONs found"},
                passed=False,
            )

        pops = {day: d.get("total_aquatic", 0) for day, d in aquatic.items()}
        max_pop = max(pops.values()) if pops else 0
        pop_365 = pops.get(365, 0)

        # --- survival: pop(day=365) / max(pop) >= 0.30 ---
        if max_pop > 0:
            frac = pop_365 / max_pop
            survival = min(frac / 0.30, 1.0)
        else:
            survival = 0.0

        # --- no_extinction: pop > 0 for all days in [30, 365] ---
        days_30_plus = [d for d in pops if d >= 30]
        if days_30_plus:
            no_ext = 1.0 if all(pops[d] > 0 for d in days_30_plus) else 0.0
        else:
            no_ext = 0.0

        # --- expansion: occupied cells @ day 365 / day 30 >= 0.20 ---
        day30_cog = _find_state_cog(run_dir, 30)
        day365_cog = _find_state_cog(run_dir, 365)
        if day30_cog and day365_cog:
            cells_30 = _count_occupied_cells(day30_cog)
            cells_365 = _count_occupied_cells(day365_cog)
            if cells_30 > 0:
                cell_frac = cells_365 / cells_30
                expansion = min(cell_frac / 0.20, 1.0)
            else:
                expansion = 0.0
        else:
            patches_30 = len(aquatic.get(30, {}).get("top_patches", []))
            patches_365 = len(aquatic.get(365, {}).get("top_patches", []))
            if patches_30 > 0:
                pfrac = patches_365 / patches_30
                expansion = min(pfrac / 0.20, 1.0)
            else:
                expansion = 0.0

        sub = [survival, no_ext, expansion]
        geo = math.prod(sub) ** (1.0 / len(sub)) if all(s > 0 for s in sub) else 0.0

        return ScorerResult(
            score=round(geo, 4),
            value=round(pop_365, 0),
            target="pop(day365) >= 30% peak, no extinction, 20% coverage",
            diagnostics={
                "sub_scores": {
                    "survival": round(survival, 4),
                    "no_extinction": round(no_ext, 4),
                    "expansion": round(expansion, 4),
                },
                "pop_day365": pop_365,
                "pop_peak": max_pop,
                "survival_fraction": round(pop_365 / max_pop, 4) if max_pop > 0 else 0.0,
                "days_evaluated": sorted(pops.keys()),
            },
            passed=geo >= 0.70,
        )
