"""Base classes for calibration scorers."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class ScorerResult:
    score: float
    value: float = 0.0
    target: str = ""
    diagnostics: dict[str, Any] = field(default_factory=dict)
    passed: bool = True

@dataclass
class ScoringReport:
    experiment_name: str
    params: dict[str, float]
    n_days: int
    n_seeds: int
    scores: dict[str, ScorerResult] = field(default_factory=dict)
    composite: float = 0.0
    llm_verdict: dict[str, Any] | None = None

class Scorer(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def weight(self) -> float: ...
    @abstractmethod
    def score(self, run_dir: Path, experiment: dict[str, Any]) -> ScorerResult: ...


# -- Shared file discovery helpers -------------------------------------------

def find_state_files(run_dir: Path) -> list[Path]:
    """Find state TIF files with either naming convention.

    Old convention: state_seed*.tif, state_day*.tif, state.tif
    New convention: *_day*.tif (e.g. ghana_abm_seed0001_day007.tif)
    """
    files = sorted(run_dir.glob("state_seed*.tif"))
    if not files:
        files = sorted(run_dir.glob("state_day*.tif"))
    if not files:
        files = sorted(run_dir.glob("*_day*.tif"))
    if not files:
        state = run_dir / "state.tif"
        if state.exists():
            files = [state]
    return files


def find_day0_file(run_dir: Path) -> Path | None:
    """Find the day-0 state file with either naming convention."""
    candidates = sorted(run_dir.glob("state_day000*.tif"))
    if not candidates:
        candidates = sorted(run_dir.glob("*_day000*.tif"))
    if candidates:
        return candidates[0]
    state = run_dir / "state.tif"
    if state.exists():
        return state
    return None


def find_day_files(run_dir: Path) -> list[Path]:
    """Find all day-snapshot TIF files with either naming convention."""
    files = sorted(run_dir.glob("state_day*.tif"))
    if not files:
        files = sorted(run_dir.glob("*_day*.tif"))
    return files


def find_cohort_file(run_dir: Path) -> Path | None:
    """Find cohort JSON with either naming convention.

    Old: cohort.json, cohort_seed*.json
    New: *_aquatic.json (e.g. ghana_abm_seed0001_aquatic.json)
    """
    cohort = run_dir / "cohort.json"
    if cohort.exists():
        return cohort
    cohorts = sorted(run_dir.glob("cohort_seed*.json"))
    if cohorts:
        return cohorts[0]
    # New convention: aquatic JSON files
    aquatic = sorted(run_dir.glob("*_aquatic.json"))
    if aquatic:
        return aquatic[0]
    return None