"""Pytest configuration for deepagents tests."""
import sys
from pathlib import Path

# Add repo root to sys.path so 'agents.*' imports work
_repo_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
