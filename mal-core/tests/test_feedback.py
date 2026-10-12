"""Tests for the canon scoring feedback module (get_feedback).

Feed it real scorecard shapes (runner.run_scoring output):
composite / verdict / gates / composite_dimensions / scores / skipped.
"""
from __future__ import annotations

from mal_core.scoring.feedback import get_feedback


def _scorecard(
    composite: float,
    dim_scores: dict[str, float] | None = None,
    gates: dict[str, bool] | None = None,
    skipped: dict[str, str] | None = None,
) -> dict:
    dims = dim_scores or {f"D{i}": composite for i in range(1, 12)}
    return {
        "run_dir": "/tmp/run",
        "composite": composite,
        "verdict": "VIABLE" if composite >= 0.70 else "BORDERLINE",
        "composite_dimensions": {
            name: {"score": s, "weight": 1.0} for name, s in dims.items()
        },
        "scores": {
            name: {"score": s, "value": s, "target": "8-15 days",
                   "diagnostics": {}, "passed": s >= 0.7, "status": "ok"}
            for name, s in dims.items()
        },
        "gates": {
            name: {"score": 1.0 if ok else 0.0, "passed": ok}
            for name, ok in (gates or {"G6_data_valid": True}).items()
        },
        "skipped": skipped or {},
    }


def test_feedback_composite_and_verdict():
    fb = get_feedback(_scorecard(0.85))
    assert "Composite: 0.8500 (VIABLE)" in fb
    assert "Weakest dimensions" in fb
    assert "Failed gates" not in fb
    assert "Skipped scorers" not in fb


def test_feedback_failed_gates_listed():
    fb = get_feedback(
        _scorecard(0.85, gates={"G6_data_valid": True, "G7_determinism": False})
    )
    assert "Failed gates: G7_determinism" in fb


def test_feedback_skipped_listed():
    fb = get_feedback(
        _scorecard(0.85, skipped={"D25_cases_ghana": "manual (AOI-dependent)"})
    )
    assert "Skipped scorers: D25_cases_ghana" in fb


def test_feedback_regression():
    cur = _scorecard(0.50, dim_scores={"D2_survival": 0.4, "D1_habitat_occupancy": 0.9})
    base = _scorecard(0.80, dim_scores={"D2_survival": 0.8, "D1_habitat_occupancy": 0.9})
    fb = get_feedback(cur, base)
    assert "Regressed dimensions: D2_survival" in fb
    assert "Baseline composite: 0.8000 -> -0.3000" in fb


def test_feedback_improvement():
    cur = _scorecard(0.85, dim_scores={"D2_survival": 0.8, "D1_habitat_occupancy": 0.9})
    base = _scorecard(0.50, dim_scores={"D2_survival": 0.4, "D1_habitat_occupancy": 0.9})
    fb = get_feedback(cur, base)
    assert "Baseline composite: 0.5000 -> +0.3500" in fb
    assert "Regressed dimensions" not in fb


def test_feedback_no_baseline():
    fb = get_feedback(_scorecard(0.85))
    assert "delta" not in fb.lower()
    assert "Baseline" not in fb
