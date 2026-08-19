"""Unit tests for Phase 3: score, diff, best."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scorers.score import save_scorecard
from scorers.diff import diff_scorecards
from scorers.best import load_best, save_best, update_best


def _make_scorecard(
    name: str,
    scores: dict[str, float],
    composite: float,
) -> dict[str, Any]:
    """Helper to create a synthetic scorecard dict."""
    return {
        "experiment": {
            "name": name,
            "params": {},
            "n_days": 90,
            "n_seeds": 1,
        },
        "scores": {
            dim: {
                "score": s,
                "value": s,
                "target": "",
                "diagnostics": {},
                "passed": s >= 0.8,
            }
            for dim, s in scores.items()
        },
        "composite": composite,
        "timestamp": "2026-07-20T00:00:00+00:00",
        "run_dir": "/tmp/test",
    }


# ── diff_scorecards ────────────────────────────────────────────────


class TestDiff:
    def test_diff_shows_improvement(self) -> None:
        """Two scorecards where b > a → delta positive."""
        dims = {"D1_expansion": 0.5, "D2_survival": 0.6}
        a = _make_scorecard("run_a", dims, composite=0.55)
        b = _make_scorecard("run_b", {"D1_expansion": 0.8, "D2_survival": 0.9}, composite=0.85)

        md = diff_scorecards(a, b)
        assert "+0.300" in md  # D1 delta
        assert "+0.300" in md  # D2 delta
        assert "+0.300" in md  # composite delta
        assert "✅" in md

    def test_diff_shows_regression(self) -> None:
        """Two scorecards where b < a → delta negative."""
        a = _make_scorecard("run_a", {"D1_expansion": 0.9}, composite=0.9)
        b = _make_scorecard("run_b", {"D1_expansion": 0.4}, composite=0.4)

        md = diff_scorecards(a, b)
        assert "-0.500" in md
        assert "❌" in md

    def test_diff_with_best(self) -> None:
        """Three scorecards: best higher than both → shows both deltas."""
        a = _make_scorecard("run_a", {"D1_expansion": 0.5}, composite=0.5)
        b = _make_scorecard("run_b", {"D1_expansion": 0.6}, composite=0.6)
        best = _make_scorecard("best", {"D1_expansion": 0.95}, composite=0.95)

        md = diff_scorecards(a, b, best)
        assert "+0.100" in md  # delta vs prev
        assert "-0.350" in md  # delta vs best
        assert "⚠️" in md     # regression vs best


# ── best tracker ───────────────────────────────────────────────────


class TestBest:
    def test_best_first_run(self, tmp_path: Path) -> None:
        """No existing best → creates one."""
        scorecard = _make_scorecard("run_1", {"D1": 0.7}, composite=0.7)
        updated, prev = update_best(scorecard, tmp_path / "run1")

        assert updated is True
        assert prev is None
        loaded = load_best(tmp_path / "run1")
        assert loaded is not None
        assert loaded["composite"] == 0.7

    def test_best_updates_on_improvement(self, tmp_path: Path) -> None:
        """Current composite > best → updates."""
        first = _make_scorecard("run_1", {"D1": 0.5}, composite=0.5)
        update_best(first, tmp_path / "run1")

        second = _make_scorecard("run_2", {"D1": 0.8}, composite=0.8)
        updated, prev = update_best(second, tmp_path / "run2")

        assert updated is True
        assert prev is not None
        assert prev["composite"] == 0.5
        loaded = load_best(tmp_path / "run2")
        assert loaded["composite"] == 0.8

    def test_best_does_not_update_on_regression(self, tmp_path: Path) -> None:
        """Current composite < best → no update."""
        first = _make_scorecard("run_1", {"D1": 0.9}, composite=0.9)
        update_best(first, tmp_path / "run1")

        second = _make_scorecard("run_2", {"D1": 0.3}, composite=0.3)
        updated, prev = update_best(second, tmp_path / "run2")

        assert updated is False
        assert prev is not None
        assert prev["composite"] == 0.9
        loaded = load_best(tmp_path / "run2")
        assert loaded["composite"] == 0.9  # unchanged


# ── save_scorecard ─────────────────────────────────────────────────


class TestSaveScorecard:
    def test_save_and_load(self, tmp_path: Path) -> None:
        scorecard = _make_scorecard("test", {"D1": 0.5}, composite=0.5)
        path = tmp_path / "scorecard.json"
        save_scorecard(scorecard, path)
        loaded = json.loads(path.read_text())
        assert loaded["composite"] == 0.5
        assert loaded["experiment"]["name"] == "test"
