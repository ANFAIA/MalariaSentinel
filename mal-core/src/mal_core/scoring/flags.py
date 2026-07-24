from typing import TypedDict, Any

class ScoringFlags(TypedDict, total=False):
    tier: str
    experiment_name: str

SCORING_FLAGS_SCHEMA: dict[str, dict[str, Any]] = {
    "tier": {"type": str, "default": "fast", "help": "Test tier (fast/full)"},
    "experiment_name": {"type": str, "default": "pipeline_run", "help": "Experiment name"},
}
