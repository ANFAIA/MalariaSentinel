"""Auto-aggregates flags from all submodules."""
from __future__ import annotations
from importlib import import_module
from typing import Any

from .stages import Stage

PIPELINE_STAGES = [s.value for s in Stage]

def aggregate_flags() -> dict[str, dict[str, dict[str, Any]]]:
    flags: dict[str, dict[str, dict[str, Any]]] = {}
    for stage in PIPELINE_STAGES:
        try:
            mod = import_module(f"mal_core.{stage}.flags")
            for attr in dir(mod):
                if attr.endswith("_FLAGS_SCHEMA"):
                    flags[stage] = getattr(mod, attr)
                    break
        except (ImportError, AttributeError):
            pass
    return flags

def get_stage_flags(stage: str) -> dict[str, dict[str, Any]]:
    return aggregate_flags().get(stage, {})
