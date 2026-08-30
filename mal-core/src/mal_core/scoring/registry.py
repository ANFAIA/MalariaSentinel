"""Scorer registry: dimensions, weights, and defaults.

Weights reflect validation value for the question "is the system good?"
— external validation and core biology dominate; engineering invariants
are gates, not dimensions (see docs/specs or AGENTS.md conventions).

Anchors (all papers live in papers/):
- D1  occupancy: Bogh 2004; Ndenga 2011 (20-70% of habitats occupied)
- D2  survival: Saarman 2019; Midega 2007 (8-15 d lifespan)
- D3  EIP: Mordecai 2013
- D11 stage structure: Bayoh & Lindsay 2003; Ouedraogo 2024
- D16 detection coverage: validate-detections launch-and-measure design
- D21 dispersal: Costantini 1996; Thomas 2013; Midega 2007 (see
  papers/anopheles-dynamics/dispersal-kernel-calibration.md)
- D25 cases: DHIMS II via Seidu 2026 (Mendeley 10.17632/r3c3cr7x6g)
"""
from __future__ import annotations

from dataclasses import dataclass

from .scorers import (
    AquaticStructureScorer,
    CasesGhanaScorer,
    CouplingScorer,
    DataValidGate,
    DetectionCoverageScorer,
    DeterminismGate,
    DispersalKernelScorer,
    EIPScorer,
    HabitatOccupancyScorer,
    HostInputGate,
    LongHorizonPersistenceScorer,
    MobilityGate,
    MoransScorer,
    PerformanceGate,
    StabilityScorer,
    SurvivalScorer,
    UrbanProductivityGate,
)
from .scorers.base import Scorer


@dataclass(frozen=True)
class ScorerSpec:
    cls: type[Scorer]
    kind: str  # "composite" | "gate"


COMPOSITE_WEIGHTS: dict[str, float] = {
    "D16_detection_coverage": 4.0,
    "D2_survival": 4.0,
    "D15_persistence": 3.0,
    "D3_eip": 3.0,
    "D8_coupling": 2.0,
    "D4_stability": 2.0,
    "D25_cases_ghana": 2.0,
    "D1_habitat_occupancy": 1.0,
    "D5_morans": 1.0,
    "D11_aquatic_structure": 1.0,
    "D21_dispersal_kernel": 1.0,
}

GATES: tuple[str, ...] = (
    "G6_data_valid",
    "G7_determinism",
    "G10_perf",
    "G12_host_input",
    "G14_mobility",
    "G24_urban_ratio",
)


def build_registry() -> dict[str, ScorerSpec]:
    instances: list[Scorer] = [
        HabitatOccupancyScorer(),    # D1
        SurvivalScorer(),            # D2
        EIPScorer(),                 # D3
        StabilityScorer(),           # D4
        MoransScorer(),              # D5
        CouplingScorer(),            # D8
        AquaticStructureScorer(),    # D11
        LongHorizonPersistenceScorer(),  # D15
        DetectionCoverageScorer(),   # D16
        DispersalKernelScorer(),     # D21
        CasesGhanaScorer(),          # D25
        DataValidGate(),             # G6
        DeterminismGate(),           # G7
        PerformanceGate(),           # G10
        HostInputGate(),             # G12
        MobilityGate(),              # G14
        UrbanProductivityGate(),     # G24
    ]
    registry: dict[str, ScorerSpec] = {}
    for scorer in instances:
        registry[scorer.name] = ScorerSpec(cls=type(scorer), kind=scorer.kind)
    return registry


def list_scorers() -> list[dict[str, str | float | bool]]:
    """Human-readable listing for ``malariasim score --list``."""
    rows: list[dict[str, str | float | bool]] = []
    for name, spec in sorted(build_registry().items()):
        scorer = spec.cls()
        rows.append(
            {
                "name": name,
                "kind": spec.kind,
                "weight": COMPOSITE_WEIGHTS.get(name, 0.0),
                "description": scorer.description,
                "manual": scorer.manual,
            }
        )
    return rows
