"""Python API for running the ABM simulation."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .wrapper import CppAbmWrapper

def run_abm(aoi: str, year: int = 2024, month: int = 1, seed: int = 1, days: int = 30, n_rollouts: int = 1, snapshot_every: int = 7, output_dir: Path | None = None, **extra_flags) -> dict[str, Any]:
    wrapper = CppAbmWrapper()
    flags: dict[str, Any] = {"aoi": aoi, "year": year, "month": month, "seed": seed, "days": days, "n_rollouts": n_rollouts, "snapshot_every": snapshot_every}
    if output_dir:
        flags["output"] = str(output_dir)
    flags.update(extra_flags)
    return wrapper.run(**flags)
