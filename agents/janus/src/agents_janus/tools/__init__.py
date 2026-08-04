"""Custom tools for the MalariaSentinel DeepAgent orchestrator."""
from .opencode_tool import opencode_search
from .gitagent_tool import (
    gitagent_init,
    gitagent_start,
    gitagent_spawn,
    gitagent_list_agents,
    gitagent_kill,
    gitagent_propose,
    gitagent_proposals,
    gitagent_diff,
    gitagent_accept,
    gitagent_reject,
    gitagent_revise,
    gitagent_integrate,
    gitagent_finalize,
)
from .pipeline_tool import (
    pipeline_run_calibration,
    pipeline_compare_scorecards,
)
from .kg_tool import memory_recall_kg
from .improve_tool import improve_prompt
from .ask_user_tool import ask_user

__all__ = [
    "opencode_search",
    "gitagent_init",
    "gitagent_start",
    "gitagent_spawn",
    "gitagent_list_agents",
    "gitagent_kill",
    "gitagent_propose",
    "gitagent_proposals",
    "gitagent_diff",
    "gitagent_accept",
    "gitagent_reject",
    "gitagent_revise",
    "gitagent_integrate",
    "gitagent_finalize",
    "pipeline_run_calibration",
    "pipeline_compare_scorecards",
    "memory_recall_kg",
    "improve_prompt",
    "ask_user",
]
