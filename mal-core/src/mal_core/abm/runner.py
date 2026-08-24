"""Python API for running the ABM simulation."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .wrapper import CppAbmWrapper

log = logging.getLogger(__name__)

# Maximum days the C++ binary accepts in a single invocation.
_CPP_MAX_DAYS = 731

# Default timeout for the C++ binary (seconds).  Single-month runs
# typically finish within 300 s; a full 731-day daily-snapshot run may
# need significantly more.  Callers can override via *timeout*.
_DEFAULT_TIMEOUT = 600


# ------------------------------------------------------------------
# Single-chunk API (one C++ invocation)
# ------------------------------------------------------------------

def run_abm(
    aoi: str,
    year: int = 2024,
    month: int = 1,
    seed: int = 1,
    days: int = 30,
    n_rollouts: int = 1,
    snapshot_every: int = 7,
    output_dir: Path | None = None,
    timeout: int | None = None,
    worktree: str | Path | None = None,
    **extra_flags,
) -> dict[str, Any]:
    """Run the ABM for a single contiguous period.

    Parameters
    ----------
    aoi : str
        Area-of-interest slug (e.g. ``"ghana"``).
    year, month : int
        Start year and month (1-indexed).
    seed : int
        RNG seed.
    days : int
        Number of simulation days (max 731 per C++ binary).
    n_rollouts : int
        Number of parallel rollouts.
    snapshot_every : int
        Write an intermediate ``*_dayNNN.tif`` every N days.
        Use ``1`` for daily snapshots.
    output_dir : Path | None
        Directory for output files.  Created if it does not exist.
    timeout : int
        Subprocess timeout in seconds (default 600).
    worktree : str | Path | None
        Optional path to a gawt worktree root for isolated binary resolution.
    **extra_flags
        Forwarded to the C++ binary as CLI flags.

    Returns
    -------
    dict
        Keys: ``stdout``, ``stderr``, ``returncode``, ``output_path``.
    """
    if days < 1 or days > _CPP_MAX_DAYS:
        raise ValueError(f"days must be 1..{_CPP_MAX_DAYS}, got {days}")

    wrapper = CppAbmWrapper(worktree=worktree)
    flags: dict[str, Any] = {
        "aoi": aoi,
        "year": year,
        "month": month,
        "seed": seed,
        "days": days,
        "n_rollouts": n_rollouts,
        "snapshot_every": snapshot_every,
    }
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        flags["output"] = str(out / f"{aoi}_abm_seed{seed:04d}.tif")
    flags.update(extra_flags)

    log.info(
        "run_abm: %s year=%d month=%d days=%d seed=%d snapshot_every=%d",
        aoi, year, month, days, seed, snapshot_every,
    )
    return wrapper.run(**flags, _timeout=timeout)
