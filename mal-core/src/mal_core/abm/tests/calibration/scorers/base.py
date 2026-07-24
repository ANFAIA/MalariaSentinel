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