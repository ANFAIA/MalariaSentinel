from typing import TypedDict, Any


class ScoringFlags(TypedDict, total=False):
    aoi: str
    only: str
    skip: str
    config_path: str


SCORING_FLAGS_SCHEMA: dict[str, dict[str, Any]] = {
    "aoi": {"type": str, "default": None, "help": "AOI slug (auto from run metadata)"},
    "only": {"type": str, "default": "", "help": "Comma-separated scorer names to run"},
    "skip": {"type": str, "default": "", "help": "Comma-separated scorer names to skip"},
    "config_path": {"type": str, "default": None, "help": "Scorers YAML config path"},
}
