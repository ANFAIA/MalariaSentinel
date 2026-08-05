"""Calibration scorers for the C++ ABM engine.

The 16 deterministic scorers (D1..D16) score ABM rollouts against a
16-dimension scorecard (see docs/specs/scoring/spec.md). The LLM scorer
in `llm_scorer.py` gives a qualitative verdict on the same report via
the OpenRouter chat/completions API.
"""

from __future__ import annotations

# Phase 3: scorecard runner, diff renderer, best tracker
from .score import score_run, save_scorecard
from .diff import diff_scorecards
from .best import load_best, save_best, update_best
