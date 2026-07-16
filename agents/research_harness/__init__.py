"""MalariaSentinel Research Harness.

An orchestrator module that calls OpenCode CLI to perform malaria research.
OpenCode uses Exa for web search — this module provides no custom search tools.
"""

from .orchestrator import run_research_cycle, run_single_phase, call_opencode
from .tools import (
    read_papers_directory,
    read_paper,
    write_paper,
    check_knowledge_gaps,
    generate_hypothesis,
)
from .config import PROJECT_ROOT, PAPERS_DIR, DEFAULT_MODEL

__all__ = [
    "run_research_cycle",
    "run_single_phase",
    "call_opencode",
    "read_papers_directory",
    "read_paper",
    "write_paper",
    "check_knowledge_gaps",
    "generate_hypothesis",
    "PROJECT_ROOT",
    "PAPERS_DIR",
    "DEFAULT_MODEL",
]
