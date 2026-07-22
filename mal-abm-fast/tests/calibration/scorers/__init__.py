"""Calibration scorers for the mal-abm-fast C++ ABM engine.

The 10 deterministic scorers (D1..D10) score ABM rollouts against a
10-dimension scorecard (see docs/calibration-test-framework.md). The
LLM scorer in `llm_scorer.py` gives a qualitative verdict on the
same report via the OpenCode Zen chat/completions API.
"""

from __future__ import annotations
