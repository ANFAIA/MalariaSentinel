"""Base classes and run-artifact discovery for post-run ABM scorers.

Promoted from mal_core/abm/tests/calibration/scorers/base.py (2026-08).
The canonical scoring home is ``mal_core.scoring``; the calibration test
suite keeps its own harness copies.

Scorers run *after* an ABM execution against its output directory
(``malariasim score --run-dir <dir>``) and produce a scorecard saved
inside that directory.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

NODATA = -9999.0


@dataclass
class ScorerResult:
    """Outcome of one scorer against one run directory.

    status:
      - "ok":      the scorer measured something real.
      - "skipped": required artifacts/dependencies are missing. Skipped
        composite dimensions are excluded from the composite (and from
        its weight sum) instead of silently scoring 1.0 ("assumed OK")
        or 0.0.
    """

    score: float = 0.0
    value: float = 0.0
    target: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)
    passed: bool = True
    status: str = "ok"  # "ok" | "skipped"

    @classmethod
    def skipped(cls, reason: str, target: str = "") -> "ScorerResult":
        return cls(
            score=0.0,
            value=0.0,
            target=target,
            diagnostics={"skipped_reason": reason},
            passed=False,
            status="skipped",
        )


class Scorer(ABC):
    """One scoring dimension or gate.

    kind:
      - "composite": biological/external-validation signal, weighted into
        the composite (weighted geometric mean).
      - "gate": binary engineering/input invariant, reported separately;
        never contributes to the composite.
    """

    name: str = ""
    kind: str = "composite"  # "composite" | "gate"
    weight: float = 1.0
    description: str = ""
    min_score: float = 0.0
    hard_floor: float = 0.0
    manual: bool = False
    """AOI-dependent scorer (needs per-AOI datasets such as occurrence
    tables, urban rasters, case series). NEVER runs by default: it must
    be explicitly activated via ``--enable`` or the scoring YAML, by an
    operator who knows the AOI has the required data."""

    @abstractmethod
    def score(self, run_dir: Path, ctx: dict[str, Any]) -> ScorerResult: ...


# -- Shared run-artifact discovery helpers -----------------------------------


def _is_transmission(name: str) -> bool:
    return "transmission" in name.lower()


def find_state_files(run_dir: Path) -> list[Path]:
    """All day-snapshot state COGs, sorted by name (day order)."""
    files = sorted(
        p for p in run_dir.glob("*_day*.tif") if not _is_transmission(p.name)
    )
    if not files:
        files = sorted(run_dir.glob("state_day*.tif"))
    if not files:
        files = sorted(run_dir.glob("state_seed*.tif"))
    if not files:
        state = run_dir / "state.tif"
        if state.exists():
            files = [state]
    return files


def find_final_state(run_dir: Path) -> Path | None:
    files = find_state_files(run_dir)
    return files[-1] if files else None


def find_day0_state(run_dir: Path) -> Path | None:
    """Earliest snapshot (day000/001, or state.tif fallback)."""
    files = find_state_files(run_dir)
    return files[0] if files else None


def find_cohort_file(run_dir: Path) -> Path | None:
    """Daily cohort JSON (adult/egg/larval counts per day).

    Current engine convention: ``<aoi>_abm_seedNNNN_cohort.json``.
    """
    for pattern in ("*_cohort.json", "cohort.json", "cohort_seed*.json"):
        matches = sorted(run_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def find_aquatic_day_files(run_dir: Path) -> list[Path]:
    """Per-day aquatic JSONs (``*_dayNNN_aquatic.json``), sorted by day."""
    return sorted(run_dir.glob("*_day*_aquatic.json"))


def find_final_aquatic(run_dir: Path) -> Path | None:
    """Final aquatic JSON (highest day, else the summary ``*_aquatic.json``)."""
    daily = find_aquatic_day_files(run_dir)
    if daily:
        return daily[-1]
    matches = sorted(run_dir.glob("*_aquatic.json"))
    return matches[0] if matches else None


def load_run_metadata(run_dir: Path) -> dict[str, Any]:
    """Load the run summary JSON (contract_version/aoi_slug/shape/...).

    The engine writes ``<aoi>_abm_seedNNNN.json`` next to the snapshots.
    """
    for path in sorted(run_dir.glob("*.json")):
        name = path.name
        if any(
            tag in name for tag in ("cohort", "aquatic", "day", "scorecard")
        ):
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and (
            "contract_version" in data or "aoi_slug" in data
        ):
            return data
    return {}


def require_aoi(ctx: dict[str, Any]) -> str | None:
    """Explicit AOI slug from ctx (CLI --aoi), never inferred.

    AOI-dependent scorers refuse to run without an explicit ``--aoi``:
    run outputs may live in any user-chosen directory, so guessing the
    AOI from paths or run metadata is forbidden by convention.
    """
    aoi = ctx.get("aoi")
    return str(aoi) if aoi else None


def grid_transform(run_dir: Path, ctx: dict[str, Any]) -> Any | None:
    """Pixel→lonlat affine for the run's state grid.

    The engine's state COGs have historically stored a garbled affine
    (GDAL order fed to an Affine constructor). The run summary JSON
    carries the correct Affine-order ``transform``. Trust the tif when
    it is north-up (b == d == 0); otherwise fall back to the run JSON.
    """
    from rasterio.transform import Affine
    import rasterio

    final = find_final_state(run_dir)
    if final is None:
        return None
    t = None
    try:
        with rasterio.open(final) as ds:
            t = ds.transform
        if abs(t.b) < 1e-12 and abs(t.d) < 1e-12:
            return t
    except Exception:
        t = None
    meta = ctx.get("run_meta") or {}
    tr = meta.get("transform")
    if isinstance(tr, (list, tuple)) and len(tr) == 6:
        return Affine(*[float(v) for v in tr])
    return t


def resolve_aoi_artifact(
    aoi: str | None, candidates: list[str]
) -> Path | None:
    """Resolve an AOI input artifact by convention, without hardcoding one AOI.

    ``candidates`` are repo-root-relative glob patterns where ``{aoi}`` is
    substituted. First existing hit wins.
    """
    if not aoi:
        return None
    root = _repo_root()
    for pattern in candidates:
        path = root / pattern.format(aoi=aoi)
        if path.exists():
            return path
        if any(ch in pattern for ch in "*?["):
            matches = sorted(root.glob(pattern.format(aoi=aoi)))
            if matches:
                return matches[0]
    return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


# -- Shared metrics helpers ---------------------------------------------------


def load_occurrence_spots(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load DEDUPLICATED (lat, lon) mosquito detection spots from a
    GBIF-style occurrence table (tab-separated, decimalLatitude/
    decimalLongitude columns)."""
    import csv

    lats: list[float] = []
    lons: list[float] = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            try:
                la = float(row["decimalLatitude"])
                lo = float(row["decimalLongitude"])
            except (KeyError, ValueError, TypeError):
                continue
            if -90 <= la <= 90 and -180 <= lo <= 180:
                lats.append(la)
                lons.append(lo)
    if not lats:
        return np.array([]), np.array([])
    pts = np.unique(np.stack([np.array(lats), np.array(lons)], axis=1), axis=0)
    return pts[:, 0], pts[:, 1]


def auc_rank(y_true: list[float] | Any, scores: Any) -> float:
    """AUC via the Mann-Whitney rank statistic (no sklearn dependency).

    ``y_true``: 1 = positive (occurrence), 0 = background.
    """
    import numpy as np

    y = np.asarray(y_true)
    s = np.asarray(scores, dtype=np.float64)
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.0
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), dtype=np.float64)
    ranks[order] = np.arange(1, len(s) + 1, dtype=np.float64)
    # average ranks for ties
    sorted_s = s[order]
    i = 0
    while i < len(sorted_s):
        j = i
        while j + 1 < len(sorted_s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        if j > i:
            avg = (i + 1 + j + 1) / 2.0
            ranks[order[i : j + 1]] = avg
        i = j + 1
    sum_pos = float(ranks[y == 1].sum())
    return (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
