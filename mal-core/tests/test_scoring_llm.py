"""Integration tests for the LLM judge (canon llm_scorer) against the
real OpenCode Zen / OpenRouter chat/completions endpoint.

Marked ``full`` and skipped unless ``OPENROUTER_KEY`` (the key the
scorer module resolves) is set. Not part of the default test run.

What they cover:
- A "perfect" synthetic scorecard yields a structurally complete
  verdict with a valid enum value.
- A "collapsed" scorecard yields a verdict in {regressed, collapsed}.
- A "borderline" scorecard is never ``viable`` and calls out D2.
- A second identical call is served from the content-hash cache.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from mal_core.scoring.llm_scorer import LLM_MODEL_DEFAULT, score_with_llm


pytestmark = [
    pytest.mark.full,
    pytest.mark.skipif(
        not os.environ.get("OPENROUTER_KEY"),
        reason="OPENROUTER_KEY not set",
    ),
]


# ---------------------------------------------------------------------------
# Synthetic scorecards
# ---------------------------------------------------------------------------


def _perfect_report() -> dict:
    return {
        "experiment": "test-perfect",
        "region": "Ghana 2024-06",
        "rollout_days": 30,
        "scores": {
            "D1_daily_survival": 0.85,
            "D2_EIP_days": 0.85,
            "D3_gonotrophic_days": 0.85,
            "D4_dispersal_km": 0.85,
            "D5_suitability_IoU": 0.85,
            "D6_density_band": 0.85,
            "D7_morans_I": 0.85,
            "D8_larval_saturation": 0.85,
            "D9_habitat_overlap": 0.85,
            "D10_age_structure": 0.85,
        },
        "composite": 0.85,
    }


def _collapsed_report() -> dict:
    return {
        "experiment": "test-collapsed",
        "region": "Ghana 2024-06",
        "rollout_days": 30,
        "scores": {
            "D1_daily_survival": 0.0,
            "D2_EIP_days": 0.0,
            "D3_gonotrophic_days": 0.0,
            "D4_dispersal_km": 0.0,
            "D5_suitability_IoU": 0.0,
            "D6_density_band": 0.0,
            "D7_morans_I": 0.0,
            "D8_larval_saturation": 0.0,
            "D9_habitat_overlap": 0.0,
            "D10_age_structure": 0.0,
        },
        "composite": 0.0,
    }


def _borderline_report() -> dict:
    return {
        "experiment": "test-borderline",
        "region": "Ghana 2024-06",
        "rollout_days": 30,
        "scores": {
            "D1_daily_survival": 0.7,
            "D2_EIP_days": 0.6,
            "D3_gonotrophic_days": 0.7,
            "D4_dispersal_km": 0.7,
            "D5_suitability_IoU": 0.7,
            "D6_density_band": 0.7,
            "D7_morans_I": 0.7,
            "D8_larval_saturation": 0.7,
            "D9_habitat_overlap": 0.7,
            "D10_age_structure": 0.7,
        },
        "composite": 0.68,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_real_llm_call_returns_valid_verdict(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    result = score_with_llm(_perfect_report(), cache_dir=cache_dir)

    assert "verdict" in result
    assert result["verdict"] in {"viable", "borderline", "regressed", "collapsed"}
    assert 0.0 <= result["composite_estimate"] <= 1.0
    assert isinstance(result["concerns"], list)
    assert isinstance(result["recommendations"], list)
    assert isinstance(result["literature_grounding"], list)
    assert result.get("model") == LLM_MODEL_DEFAULT
    assert isinstance(result.get("latency_s"), (int, float))


def test_real_llm_call_on_collapsed_experiment(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    result = score_with_llm(_collapsed_report(), cache_dir=cache_dir)

    assert result["verdict"] in {"regressed", "collapsed"}, (
        f"Expected regressed/collapsed for zeroed report, got {result['verdict']!r}"
    )
    assert result["composite_estimate"] < 0.6
    assert any(c.startswith("D") for c in result["concerns"])


def test_real_llm_call_on_borderline_experiment(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    result = score_with_llm(_borderline_report(), cache_dir=cache_dir)

    assert result["verdict"] != "viable", (
        f"Expected non-viable for borderline report, got viable: {result!r}"
    )
    assert any("D2" in c for c in result["concerns"]), (
        f"Expected D2 in concerns for borderline report, got {result['concerns']!r}"
    )


def test_real_llm_response_is_cached(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    report = _perfect_report()

    first = score_with_llm(report, cache_dir=cache_dir)
    second = score_with_llm(report, cache_dir=cache_dir)

    assert first["verdict"] == second["verdict"]
    assert first["composite_estimate"] == second["composite_estimate"]
    assert second.get("cache_hit") is True
