"""D12: Host density conservation — total humans match census reference."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from scorers.base import Scorer, ScorerResult


class HostDensityScorer(Scorer):
    @property
    def name(self) -> str:
        return "D12_host_density"

    @property
    def weight(self) -> float:
        return 2.0

    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult:
        hosts_path = experiment.get("hosts_path") or self._find_hosts_nc(run_dir)
        if hosts_path is None:
            return ScorerResult(
                score=0.0,
                value=0.0,
                target="human total ~ 27M (Ghana 2019)",
                diagnostics={"error": "host_static.nc not found"},
                passed=False,
            )

        import xarray as xr

        ds = xr.open_dataset(str(hosts_path), engine="netcdf4")

        human = ds["human"].values
        valid = human[human != -9999.0]
        human_total = float(valid.sum()) if valid.size > 0 else 0.0

        ref_total = experiment.get("human_reference_total", 27_000_000)

        if ref_total > 0:
            ratio = human_total / ref_total
            if 0.9 <= ratio <= 1.1:
                raw = 1.0
            elif 0.8 <= ratio <= 1.2:
                raw = math.exp(-((ratio - 1.0) / 0.15) ** 2)
            elif 0.5 <= ratio <= 1.5:
                raw = math.exp(-((ratio - 1.0) / 0.3) ** 2)
            else:
                raw = 0.0
        else:
            raw = 0.0

        return ScorerResult(
            score=round(raw, 4),
            value=round(human_total, 0),
            target=f"human total ~ {ref_total:,.0f} (Ghana 2019)",
            diagnostics={
                "human_total": round(human_total, 0),
                "reference_total": ref_total,
                "ratio": round(human_total / ref_total, 4) if ref_total > 0 else 0,
            },
            passed=raw >= 0.70,
        )

    def _find_hosts_nc(self, run_dir: Path) -> Path | None:
        candidates = [
            run_dir / "host_static.nc",
            run_dir.parent / "hosts" / "host_static.nc",
            Path("data/ghana/host_static.nc"),
            Path("/tmp/hosts_ghana/host_static.nc"),
        ]
        for p in candidates:
            if p.exists():
                return p
        return None
