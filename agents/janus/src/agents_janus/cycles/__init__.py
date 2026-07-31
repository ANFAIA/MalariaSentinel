"""Predefined improvement cycles for the MalariaSentinel DeepAgent.

Unified cycle architecture (M10.5+):
- run_cycle: single entry point, auto-detects mode from goal
- run_calibration_cycle / run_feature_cycle / run_research_cycle: backwards-compat aliases

The orchestrator handles all goal types (calibration, features, research, bugs)
through one methodology. The mode is a hint about emphasis, not a hard constraint.
"""
from agents_janus.cycles.run_cycle import (
    run_cycle,
    run_calibration_cycle,
    run_feature_cycle,
    run_research_cycle,
)

__all__ = [
    "run_cycle",
    "run_calibration_cycle",
    "run_feature_cycle",
    "run_research_cycle",
]