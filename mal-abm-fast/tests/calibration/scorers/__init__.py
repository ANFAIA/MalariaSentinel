"""Calibration scorers for the mal-abm-fast C++ ABM engine.

The 10 deterministic scorers (D1..D10) score ABM rollouts against a
10-dimension scorecard (see docs/calibration-test-framework.md). The
LLM scorer in `llm_scorer.py` gives a qualitative verdict on the
same report via the OpenCode Zen chat/completions API.
"""

from __future__ import annotations

# Phase 3: scorecard runner, diff renderer, best tracker
from scorers.score import score_run, save_scorecard
from scorers.diff import diff_scorecards
from scorers.best import load_best, save_best, update_best
