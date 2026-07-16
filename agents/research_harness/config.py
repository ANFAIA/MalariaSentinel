"""Configuration for the MalariaSentinel research harness."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PAPERS_DIR = PROJECT_ROOT / "papers"
SKILLS_DIR = Path(__file__).parent / "skills"
MEMORY_FILE = Path(__file__).parent / "AGENTS.md"

DEFAULT_TOPICS = [
    "malaria mosquito ABM geospatial analysis",
    "spatial decision support systems malaria elimination",
    "Anopheles gambiae population dynamics modeling",
    "malaria transmission risk mapping Africa",
    "agent-based models malaria intervention evaluation",
]

# Model configuration — MIMO V2.5 is the default and only model
# Override via OPENCODE_MODEL env var or --model CLI flag
DEFAULT_MODEL = "opencode-go/mimo-v2.5"
OPENCODE_MODEL = None  # Resolved at runtime: env var > CLI flag > DEFAULT_MODEL
OPENCODE_TIMEOUT = 300  # seconds per call
