from typing import TypedDict, Any

class AbmFlags(TypedDict, total=False):
    aoi: str
    year: int
    month: int
    seed: int
    days: int
    n_rollouts: int
    snapshot_every: int
    env: str
    habitat: str
    output: str

ABM_FLAGS_SCHEMA: dict[str, dict[str, Any]] = {
    "aoi": {"type": str, "default": None, "help": "AOI slug (e.g. ghana)"},
    "year": {"type": int, "default": 2024, "help": "Start year"},
    "month": {"type": int, "default": 1, "help": "Start month (1-12)"},
    "seed": {"type": int, "default": 1, "help": "Random seed"},
    "days": {"type": int, "default": 30, "help": "Simulation duration in days"},
    "n_rollouts": {"type": int, "default": 1, "help": "Number of rollouts"},
    "snapshot_every": {"type": int, "default": 7, "help": "Snapshot interval in days"},
    "env": {"type": str, "default": None, "help": "Path to env GeoTIFF"},
    "habitat": {"type": str, "default": None, "help": "Path to habitat GeoPackage"},
    "output": {"type": str, "default": None, "help": "Output directory"},
}
