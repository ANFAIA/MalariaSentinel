#!/usr/bin/env python3
"""MalariaSentinel DeepAgent CLI — convenience wrapper.

Usage:
    ./agents/deepagents/run.py calibration -g "goal"
    ./agents/deepagents/run.py feature "name" "description" -g "goal"
    ./agents/deepagents/run.py research "topic" -g "goal"
    ./agents/deepagents/run.py run -g "goal"

Or via module:
    uv run python -m agents.janus calibration -g "goal"
"""
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so agents.janus is importable
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from agents.janus.cli import app

app()
