"""D25: Ghana DHIMS-II reported-cases match (Ghana-only, manual).

Compares the simulated malaria transmission seasonality against the
real reported-cases climatology from the Ghana Health Service DHIMS II
dataset (Seidu 2026, Mendeley Data DOI 10.17632/r3c3cr7x6g): monthly
reported malaria cases for Ashanti, Eastern and Volta regions,
Jan 2016 - Dec 2023, 288 rows, zero gaps. FIXED dataset: the scorer
downloads it itself (URL + SHA-256 pinned below) if not already in
``data/ghana/scoring/dhis2_cases.csv``.

Score: Pearson correlation between the SIMULATED calendar-month
climatology (mean daily human incidence per month from the
``*_transmission_daily.json`` log written by ``--enable-transmission``
runs) and the OBSERVED calendar-month climatology (pooled mean monthly
cases of the 3 regions, Covid-2020 months excluded via the dataset's
own Covid flag). r >= 0.6 -> 1.0, Gaussian decay below.

Ghana-only by construction: the dataset covers 3 of Ghana's 16 regions
and carries no population denominators, so it does not generalize to
other AOIs. Region-level only — no district data.

AOI-dependent (manual activation, explicit ``--aoi ghana`` required).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np

from .base import Scorer, ScorerResult, require_aoi, _repo_root

DATASET_URL = (
    "https://data.mendeley.com/public-files/datasets/r3c3cr7x6g/files/"
    "d8fc241d-9834-467f-8d82-56241fab6ee9/file_downloaded"
)
DATASET_SHA256 = "e19f0ef16338a413ad5195ce4e2ee19af9991b85ac61915fe7702f6576c81202"
DATASET_SUBPATH = "data/ghana/scoring/dhis2_cases.csv"
R_TARGET = 0.60

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _dataset_path() -> Path:
    return _repo_root() / DATASET_SUBPATH


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def ensure_dataset() -> Path:
    """Download the fixed DHIMS dataset if absent or checksum mismatch."""
    path = _dataset_path()
    if path.exists() and _sha256(path) == DATASET_SHA256:
        return path
    import urllib.request

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    req = urllib.request.Request(DATASET_URL, headers={"User-Agent": "malariasim"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as f:
        f.write(resp.read())
    if _sha256(tmp) != DATASET_SHA256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("DHIMS dataset checksum mismatch — refusing to use")
    tmp.replace(path)
    return path


def _observed_climatology(path: Path) -> np.ndarray:
    """Mean reported cases per calendar month, pooled regions, 2020 masked."""
    sums = np.zeros(12)
    counts = np.zeros(12)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            period = (row.get("Period") or "").strip()  # e.g. 'Jan-16'
            m = re.match(r"^([A-Z][a-z]{2})-(\d{2})$", period)
            if not m:
                continue
            mon, yy = m.group(1), int(m.group(2))
            year = 2000 + yy
            if year == 2020:  # Covid care-seeking disruption (dataset Covid flag)
                continue
            try:
                cases = float(row["Malaria"])
            except (KeyError, ValueError, TypeError):
                continue
            idx = _MONTHS.index(mon)
            sums[idx] += cases
            counts[idx] += 1
    counts[counts == 0] = 1
    return sums / counts


def _observed_year_series(path: Path, year: int) -> np.ndarray | None:
    """Total reported cases per month for ONE calendar year (pooled regions)."""
    sums = np.zeros(12)
    seen = np.zeros(12, dtype=bool)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            period = (row.get("Period") or "").strip()
            m = re.match(r"^([A-Z][a-z]{2})-(\d{2})$", period)
            if not m:
                continue
            mon, yy = m.group(1), 2000 + int(m.group(2))
            if yy != year:
                continue
            try:
                cases = float(row["Malaria"])
            except (KeyError, ValueError, TypeError):
                continue
            idx = _MONTHS.index(mon)
            sums[idx] += cases
            seen[idx] = True
    return sums if seen.all() else None


def _simulated_monthly_totals(
    run_dir: Path, start_year: int, start_month: int = 1,
) -> tuple[np.ndarray, list[int]] | None:
    """Total incidence per 30-day block from the transmission log.

    Returns (totals_per_block, calendar_years_per_block) or None.
    """
    logs = sorted(run_dir.glob("*_transmission_daily.json"))
    if not logs:
        return None
    try:
        data = json.loads(logs[0].read_text())
    except (json.JSONDecodeError, OSError):
        return None
    daily = data.get("daily", [])
    if len(daily) < 30:
        return None
    n_blocks = len(daily) // 30
    totals = np.zeros(n_blocks)
    years: list[int] = []
    for entry in daily:
        day = int(entry.get("day", 0))
        block = day // 30
        if block >= n_blocks:  # partial trailing block
            continue
        totals[block] += float(entry.get("incidence", 0.0))
    for b in range(n_blocks):
        year = start_year + (start_month - 1 + b) // 12
        years.append(year)
    return totals, years


def _simulated_climatology(run_dir: Path, start_month: int = 1) -> np.ndarray | None:
    """DEPRECATED: kept for the climatology fallback path; use
    _simulated_monthly_totals + _observed_climatology instead."""
    totals = _simulated_monthly_totals(run_dir, start_year=2024, start_month=start_month)
    if totals is None:
        return None
    sim_totals, _ = totals
    sums = np.zeros(12)
    counts = np.zeros(12)
    for b, total in enumerate(sim_totals):
        idx = (start_month - 1 + b) % 12
        sums[idx] += total
        counts[idx] += 1
    counts[counts == 0] = 1
    return sums / counts


class CasesGhanaScorer(Scorer):
    name = "D25_cases_ghana"
    kind = "composite"
    weight = 2.0
    description = "Seasonality match vs DHIMS-II reported cases, Ghana-only (Seidu 2026)"
    min_score = 0.5
    hard_floor = 0.2
    manual = True  # Ghana-only: fixed national dataset, not generalizable

    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult:
        aoi = require_aoi(ctx)
        if not aoi:
            return ScorerResult.skipped(
                "requires explicit --aoi (never inferred)", target="seasonality r"
            )
        if aoi != "ghana":
            return ScorerResult.skipped(
                f"Ghana-only score: dataset covers Ashanti/Eastern/Volta (Ghana), "
                f"not AOI {aoi!r}",
                target="seasonality r",
            )

        run_meta = ctx.get("run_meta") or {}
        start_year = int(run_meta.get("year", 2024) or 2024)
        start_month = int(run_meta.get("month", 1) or 1)
        monthly = _simulated_monthly_totals(
            run_dir, start_year=start_year, start_month=start_month
        )
        if monthly is None:
            return ScorerResult.skipped(
                "no *_transmission_daily.json — requires a run with "
                "--enable-transmission",
                target="seasonality r",
            )
        try:
            path = ensure_dataset()
        except Exception as e:
            return ScorerResult.skipped(f"dataset unavailable: {e}", target="seasonality r")

        warmup = int(ctx.get("warmup_months", 12) or 0)
        sim_totals, sim_years = monthly
        n_blocks = len(sim_totals)
        # aligned mode: compare the LAST full 12 blocks (post warm-up) with
        # the observed series of their calendar year, when that year exists
        # in the dataset and the tail covers one full year.
        tail_year = sim_years[n_blocks - 1]
        full_year_tail = (
            n_blocks >= warmup + 12
            and len(set(sim_years[n_blocks - 12 : n_blocks])) == 1
        )
        if full_year_tail and _observed_year_series(path, tail_year) is not None:
            sim = sim_totals[n_blocks - 12 : n_blocks]
            obs = _observed_year_series(path, tail_year)
            assert obs is not None  # narrowed above
            mode = f"aligned-{tail_year}"
            target = f"seasonality r >= {R_TARGET} vs observed {tail_year}"
        else:
            # fallback: month-of-year climatology vs 2016-2023 pooled
            sims = np.zeros(12)
            counts = np.zeros(12)
            for b in range(warmup, n_blocks):
                cal_month = (start_month - 1 + b) % 12
                sims[cal_month] += sim_totals[b]
                counts[cal_month] += 1
            counts[counts == 0] = 1
            sim = sims / counts
            obs = _observed_climatology(path)
            mode = "climatology"
            target = f"seasonality r >= {R_TARGET} (monthly climatology)"

        if obs.std() == 0 or sim.std() == 0:
            return ScorerResult.skipped(
                "degenerate series (zero variance)", target
            )
        r = float(np.corrcoef(sim, obs)[0, 1])
        if np.isnan(r):
            r = 0.0
        if r >= R_TARGET:
            score = 1.0
        else:
            score = max(0.0, math.exp(-((r - R_TARGET) / 0.20) ** 2))
        return ScorerResult(
            score=round(score, 4),
            value=round(r, 4),
            target=target,
            diagnostics={
                "mode": mode,
                "dataset": str(path.name),
                "warmup_months": warmup,
                "observed": [round(float(v), 1) for v in obs],
                "simulated": [round(float(v), 6) for v in sim],
                "covid_2020_excluded": True,
            },
            passed=score >= self.min_score,
        )
