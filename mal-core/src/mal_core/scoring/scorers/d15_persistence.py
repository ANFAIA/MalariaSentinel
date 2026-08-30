"""D15: Long-horizon population persistence.

Catches long-run demographic failures (e.g. the day-90 crash class)
that 30-day scorers never see. Three sub-scores (geometric mean):

- survival: pop(last day) >= 30% of peak
- no_extinction: total aquatic > 0 for every sampled day >= 30
- expansion: occupied cells at last day >= 20% of cells at day 30
  (from state COGs; falls back to top_patches counts)

Horizon = last available day (>= 30). Runs shorter than 30 days are
skipped.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .base import NODATA, Scorer, ScorerResult, find_aquatic_day_files, find_state_files

_DAY_RE = re.compile(r"_day(\d+)_aquatic\.json$")


def _parse_day(path: Path) -> int | None:
    m = _DAY_RE.search(path.name)
    return int(m.group(1)) if m else None


def _load_aquatic_pop(run_dir: Path) -> dict[int, int]:
    pops: dict[int, int] = {}
    for p in find_aquatic_day_files(run_dir):
        day = _parse_day(p)
        if day is None:
            continue
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        pops[day] = int(data.get("total_aquatic", 0))
    return pops


def _count_occupied(tif_path: Path, threshold: float = 0.05) -> int | None:
    try:
        import numpy as np
        import rasterio
    except ImportError:
        return None
    try:
        with rasterio.open(tif_path) as ds:
            band = ds.read(1)
        valid = np.isfinite(band) & (band != NODATA)
        return int((valid & (band > threshold)).sum())
    except Exception:
        return None


class LongHorizonPersistenceScorer(Scorer):
    name = "D15_persistence"
    kind = "composite"
    weight = 3.0
    description = "Population survives the horizon: no extinction, 30% of peak, expansion"
    min_score = 0.7
    hard_floor = 0.4

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        pops = _load_aquatic_pop(run_dir)
        if not pops:
            return ScorerResult.skipped(
                "no aquatic day JSONs",
                target="pop(last) >=30% peak, no extinction, 20% cells vs day30",
            )
        last_day = max(pops)
        if last_day < 30:
            return ScorerResult.skipped(
                f"run too short for persistence check (last day {last_day} < 30)",
                target="pop(last) >=30% peak, no extinction, 20% cells vs day30",
            )
        max_pop = max(pops.values())
        pop_last = pops[last_day]

        survival = min(pop_last / max_pop / 0.30, 1.0) if max_pop > 0 else 0.0

        days_30_plus = [d for d in pops if d >= 30]
        no_ext = 1.0 if days_30_plus and all(pops[d] > 0 for d in days_30_plus) else 0.0

        # expansion: occupied cells last vs day 30
        expansion = 0.0
        cogs = find_state_files(run_dir)
        cog_by_day: dict[int, Path] = {}
        for c in cogs:
            m = re.search(r"_day(\d+)\.tif$", c.name)
            if m:
                cog_by_day[int(m.group(1))] = c
        base_day = min(d for d in cog_by_day if d >= 30) if any(
            d >= 30 for d in cog_by_day
        ) else None
        if base_day is not None and last_day in cog_by_day:
            cells_base = _count_occupied(cog_by_day[base_day])
            cells_last = _count_occupied(cog_by_day[last_day])
            if cells_base and cells_last is not None and cells_base > 0:
                expansion = min((cells_last / cells_base) / 0.20, 1.0)
        if expansion == 0.0:
            # fallback: top_patches counts from the aquatic JSONs
            def _patches_from(day: int) -> int:
                for p in find_aquatic_day_files(run_dir):
                    if _parse_day(p) == day:
                        try:
                            return len(json.loads(p.read_text()).get("top_patches", []))
                        except (json.JSONDecodeError, OSError):
                            return 0
                return 0

            p_base = _patches_from(base_day) if base_day is not None else 0
            p_last = _patches_from(last_day)
            if p_base > 0:
                expansion = min((p_last / p_base) / 0.20, 1.0)

        subs = [survival, no_ext, expansion]
        geo = (
            math.prod(subs) ** (1.0 / len(subs)) if all(s > 0 for s in subs) else 0.0
        )
        return ScorerResult(
            score=round(geo, 4),
            value=float(pop_last),
            target="pop(last) >=30% peak, no extinction, 20% cells vs day30",
            diagnostics={
                "sub_scores": {k: round(v, 4) for k, v in zip(
                    ("survival", "no_extinction", "expansion"), subs)},
                "last_day": last_day,
                "pop_last": pop_last,
                "pop_peak": max_pop,
                "days_sampled": len(pops),
            },
            passed=geo >= self.min_score,
        )
