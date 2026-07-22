"""Integration tests for the LLM scorer against a real OpenCode Zen
endpoint.

These tests are marked ``@pytest.mark.full`` and skipped unless
``OPENCODE_API_KEY`` is set in the environment. They exercise the
end-to-end happy path against the real chat/completions API and are
NOT part of the default fast tier.

What they cover:

- A "perfect" synthetic report (all 10 dimensions at 0.85) yields a
  verdict in the valid enum and a structurally complete response.
- A "collapsed" synthetic report (key dimensions at 0.0) yields a
  verdict in ``{regressed, collapsed}``.
- A "borderline" synthetic report (one dimension marginal) yields a
  verdict that is NOT ``viable`` and lists at least one specific
  dimension in its concerns.
- A second call with the same report returns the same verdict and is
  served from the content-hash cache (no second LLM call).

Each test uses a ``tmp_path`` cache directory so the test never
collides with a real calibration run's cache.

Run with:

    cd mal-abm-fast/tests/calibration
    OPENCODE_API_KEY=sk-... uv run pytest tests/test_llm_integration.py -v -m full
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scorers.llm_scorer import LLM_MODEL_DEFAULT, score_with_llm


pytestmark = [
    pytest.mark.full,
    pytest.mark.skipif(
        not os.environ.get("OPENCODE_API_KEY"),
        reason="OPENCODE_API_KEY not set",
    ),
]


# ---------------------------------------------------------------------------
# Synthetic reports
# ---------------------------------------------------------------------------


def _perfect_report() -> dict:
    """A synthetic "perfect" calibration report — all 10 dimensions
    comfortably within the reference ranges, composite 0.85."""
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
    """A synthetic "collapsed" calibration report — D2, D3, D4 at 0.0
    and the rest of the dimensions at 0.0 too. Should land in
    ``regressed`` or ``collapsed``."""
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
    """A synthetic "borderline" calibration report — D2 is marginal
    (0.6, just below the 0.80 viable threshold for EIP-related scores),
    everything else at 0.7. Should NOT come back as ``viable`` and
    should flag D2 in the concerns."""
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
    """A "perfect" report round-trips through the real LLM and comes
    back as a structurally complete Verdict with a valid enum value."""
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
    """A "collapsed" report (key dimensions at 0.0) must come back as
    ``regressed`` or ``collapsed`` — never ``viable`` or ``borderline``."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    result = score_with_llm(_collapsed_report(), cache_dir=cache_dir)

    assert result["verdict"] in {"regressed", "collapsed"}, (
        f"Expected regressed/collapsed for zeroed report, got {result['verdict']!r}"
    )
    assert result["composite_estimate"] < 0.6
    # At least one concern should call out a dimension.
    assert any(c.startswith("D") for c in result["concerns"])


def test_real_llm_call_on_borderline_experiment(tmp_path: Path) -> None:
    """A "borderline" report (D2 marginal) must NOT be classified
    ``viable`` and must call out specific dimensions in the concerns."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    result = score_with_llm(_borderline_report(), cache_dir=cache_dir)

    assert result["verdict"] != "viable", (
        f"Expected non-viable for borderline report, got viable: {result!r}"
    )
    # The concerns should mention at least one dimension by id.
    assert any("D2" in c for c in result["concerns"]), (
        f"Expected D2 in concerns for borderline report, got {result['concerns']!r}"
    )


def test_real_llm_response_is_cached(tmp_path: Path) -> None:
    """The second call with the same report must return the cached
    verdict (same value, ``cache_hit=True``) — proving the
    content-hash cache works in real life, not just in unit tests."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    report = _perfect_report()

    first = score_with_llm(report, cache_dir=cache_dir)
    second = score_with_llm(report, cache_dir=cache_dir)

    assert first["verdict"] == second["verdict"]
    assert first["composite_estimate"] == second["composite_estimate"]
    assert second.get("cache_hit") is True
