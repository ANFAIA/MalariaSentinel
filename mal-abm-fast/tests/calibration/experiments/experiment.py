"""Experiment dataclass and runner."""
from __future__ import annotations
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class Experiment:
    name: str
    params: dict[str, Any]
    env_path: str
    habitat_path: str
    aoi: str = "ghana"
    n_days: int = 90
    seeds: list[int] = field(default_factory=lambda: [1])
    seeding_mode: str = "uniform"
    snapshot_every: int = 1

    def run(self, cpp_binary: Path, output_dir: Path) -> dict[str, Any]:
        """Run the experiment via the C++ CLI. Returns run metadata."""
        output_dir.mkdir(parents=True, exist_ok=True)
        state_path = output_dir / "state.tif"
        cohort_path = output_dir / "cohort.json"
        cmd = [
            str(cpp_binary), "run",
            "--aoi", self.aoi,
            "--year", "2024", "--month", "6",
            "--seed", str(self.seeds[0]),
            "--days", str(self.n_days),
            "--n-rollouts", str(len(self.seeds)),
            "--snapshot-every", str(self.snapshot_every),
            "--env", self.env_path,
            "--habitat", self.habitat_path,
            "--output", str(state_path),
            "--seeding-mode", self.seeding_mode,
            "--emit-cohort-log", str(cohort_path),
        ]
        t0 = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        wall_s = time.perf_counter() - t0
        if result.returncode != 0:
            raise RuntimeError(f"ABM run failed: {result.stderr[-500:]}")
        # Collect state COG paths
        state_cogs = sorted(output_dir.glob("state_seed*.tif"))
        if not state_cogs and state_path.exists():
            state_cogs = [state_path]
        return {
            "state_cogs": [str(p) for p in state_cogs],
            "cohort_log": str(cohort_path) if cohort_path.exists() else None,
            "wall_s": wall_s,
            "stdout": result.stdout,
        }
