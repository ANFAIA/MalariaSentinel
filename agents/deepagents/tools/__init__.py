"""Custom tools for the MalariaSentinel DeepAgent orchestrator."""
from .opencode_tool import opencode_search
from .gitagent_tool import (
    gitagent_spawn,
    gitagent_proposals,
    gitagent_integrate,
    gitagent_finalize,
)
from .pipeline_tool import (
    pipeline_run_calibration,
    pipeline_compare_scorecards,
)
from .kg_tool import memory_recall_kg
from .improve_tool import improve_prompt

__all__ = [
    "opencode_search",
    "gitagent_spawn",
    "gitagent_proposals",
    "gitagent_integrate",
    "gitagent_finalize",
    "pipeline_run_calibration",
    "pipeline_compare_scorecards",
    "memory_recall_kg",
    "improve_prompt",
]
