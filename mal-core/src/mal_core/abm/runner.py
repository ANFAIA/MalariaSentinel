"""Python API for running the ABM simulation."""
from __future__ import annotations

import calendar
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .wrapper import CppAbmWrapper

log = logging.getLogger(__name__)

# Maximum days the C++ binary accepts in a single invocation.
_CPP_MAX_DAYS = 730

# Default timeout for the C++ binary (seconds).  Single-month runs
# typically finish within 300 s; a full 730-day daily-snapshot run may
# need significantly more.  Callers can override via *timeout*.
_DEFAULT_TIMEOUT = 600


def _month_days(year: int, month: int) -> int:
    """Return the number of calendar days in *year*-*month*."""
    return calendar.monthrange(year, month)[1]


def _next_month(year: int, month: int) -> tuple[int, int]:
    """Return the (year, month) of the next calendar month."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


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
    timeout: int = _DEFAULT_TIMEOUT,
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
        Number of simulation days (max 730 per C++ binary).
    n_rollouts : int
        Number of parallel rollouts.
    snapshot_every : int
        Write an intermediate ``*_dayNNN.tif`` every N days.
        Use ``1`` for daily snapshots.
    output_dir : Path | None
        Directory for output files.  Created if it does not exist.
    timeout : int
        Subprocess timeout in seconds (default 600).
    **extra_flags
        Forwarded to the C++ binary as CLI flags.

    Returns
    -------
    dict
        Keys: ``stdout``, ``stderr``, ``returncode``, ``output_path``.
    """
    if days < 1 or days > _CPP_MAX_DAYS:
        raise ValueError(f"days must be 1..{_CPP_MAX_DAYS}, got {days}")

    wrapper = CppAbmWrapper()
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


# ------------------------------------------------------------------
# Full-period API (may split into multiple C++ invocations)
# ------------------------------------------------------------------

def run_abm_full_period(
    aoi: str,
    year: int = 2024,
    month: int = 1,
    end_year: int | None = None,
    end_month: int | None = None,
    seed: int = 1,
    n_rollouts: int = 1,
    snapshot_every: int = 1,
    output_dir: Path | str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
    max_chunk_days: int = _CPP_MAX_DAYS,
    **extra_flags,
) -> dict[str, Any]:
    """Run the ABM across one or more calendar months.

    The simulation may be split into monthly chunks (or chunks of
    *max_chunk_days* days) to stay within the C++ binary's 730-day
    limit and to keep subprocess timeouts reasonable.

    Parameters
    ----------
    aoi : str
        Area-of-interest slug.
    year, month : int
        Start year and month.
    end_year, end_month : int | None
        End year and month (inclusive).  Defaults to the same as
        *year*/*month* (single-month run).
    seed : int
        RNG seed.  Each chunk re-seeds from this base.
    n_rollouts : int
        Parallel rollouts.
    snapshot_every : int
        Daily snapshots (``1``) or weekly (``7``).
    output_dir : Path | str | None
        Output directory.  Created automatically.
    timeout : int
        Per-chunk subprocess timeout in seconds.
    max_chunk_days : int
        Maximum days per C++ invocation (default 730).
    **extra_flags
        Forwarded to the C++ binary.

    Returns
    -------
    dict
        Aggregated results from all chunks.
    """
    if end_year is None:
        end_year = year
    if end_month is None:
        end_month = month

    if output_dir is None:
        out_dir = Path("runs") / aoi
    else:
        out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # -- Build a list of (year, month, days) chunks -------------------
    chunks: list[tuple[int, int, int]] = []
    cur_y, cur_m = year, month
    while (cur_y, cur_m) <= (end_year, end_month):
        days_in_month = _month_days(cur_y, cur_m)
        # Split at max_chunk_days boundary if needed
        remaining = days_in_month
        day_offset = 0
        while remaining > 0:
            chunk_days = min(remaining, max_chunk_days)
            chunks.append((cur_y, cur_m, chunk_days))
            remaining -= chunk_days
            day_offset += chunk_days
        cur_y, cur_m = _next_month(cur_y, cur_m)

    total_days = sum(c[2] for c in chunks)
    log.info(
        "run_abm_full_period: %s %d-%02d to %d-%02d = %d days in %d chunk(s)",
        aoi, year, month, end_year, end_month, total_days, len(chunks),
    )

    results: list[dict[str, Any]] = []
    cur_date = date(year, month, 1)

    for i, (cy, cm, cdays) in enumerate(chunks):
        log.info(
            "  chunk %d/%d: year=%d month=%d days=%d",
            i + 1, len(chunks), cy, cm, cdays,
        )
        # Output file for this chunk's final snapshot
        chunk_out = out_dir / f"{aoi}_abm_seed{seed:04d}_chunk{i:03d}.tif"
        flags: dict[str, Any] = {
            "aoi": aoi,
            "year": cy,
            "month": cm,
            "seed": seed,
            "days": cdays,
            "n_rollouts": n_rollouts,
            "snapshot_every": snapshot_every,
            "output": str(chunk_out),
        }
        flags.update(extra_flags)

        wrapper = CppAbmWrapper()
        result = wrapper.run(**flags, _timeout=timeout)
        result["chunk"] = i
        result["chunk_year"] = cy
        result["chunk_month"] = cm
        result["chunk_days"] = cdays
        result["output_path"] = str(chunk_out)
        results.append(result)

        # Advance the logical date by cdays
        cur_date += timedelta(days=cdays)

    # Summarise
    all_ok = all(r.get("returncode", -1) == 0 for r in results)
    combined: dict[str, Any] = {
        "success": all_ok,
        "total_days": total_days,
        "n_chunks": len(chunks),
        "output_dir": str(out_dir),
        "chunks": results,
    }
    if results:
        combined["last_stdout"] = results[-1].get("stdout", "")
        combined["last_stderr"] = results[-1].get("stderr", "")

    return combined
