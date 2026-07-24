"""Unit tests for Phase 3: score, diff, best."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scorers.score import score_run, save_scorecard
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


# ── score_run ──────────────────────────────────────────────────────


class TestScoreRun:
    def test_score_run_produces_scorecard(self, tmp_path: Path) -> None:
        """score_run produces a scorecard with all 10 dims + composite."""
        import numpy as np
        import rasterio
        from rasterio.transform import from_bounds

        # Create minimal COG files so at least some scorers produce non-zero scores
        b0 = np.zeros((10, 10), dtype=np.float32)
        b0[5, 5] = 0.8
        b1 = np.zeros((10, 10), dtype=np.float32)
        transform = from_bounds(-1.5, 4.5, 1.5, 11.5, 10, 10)
        with rasterio.open(
            tmp_path / "state_seed0001.tif",
            "w",
            driver="GTiff",
            height=10,
            width=10,
            count=2,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
            nodata=-9999.0,
        ) as dst:
            dst.write(b0, 1)
            dst.write(b1, 2)

        experiment = {"name": "test_exp", "params": {}, "n_days": 30, "n_seeds": 1}
        scorecard = score_run(tmp_path, experiment)

        # Check structure
        assert "experiment" in scorecard
        assert "scores" in scorecard
        assert "composite" in scorecard
        assert "timestamp" in scorecard
        assert "run_dir" in scorecard

        # Check all 10 dimensions present
        expected_dims = {
            "D1_expansion", "D2_survival", "D3_eip", "D4_stability",
            "D5_morans", "D6_mass", "D7_determinism", "D8_coupling",
            "D9_activation", "D10_perf",
        }
        assert set(scorecard["scores"].keys()) == expected_dims

        # Each score entry has the right keys
        for dim, entry in scorecard["scores"].items():
            assert "score" in entry
            assert "value" in entry
            assert "passed" in entry
            assert isinstance(entry["score"], float)

    def test_score_run_handles_missing_files(self, tmp_path: Path) -> None:
        """Empty run_dir → most scorers return 0.0, composite is 0.0."""
        experiment = {"name": "empty", "params": {}, "n_days": 1, "n_seeds": 1}
        scorecard = score_run(tmp_path, experiment)

        assert scorecard["composite"] == 0.0
        # D7_determinism and D10_perf return 1.0 when files are missing (defaults to OK)
        exempt_dims = {"D7_determinism", "D10_perf"}
        for dim, entry in scorecard["scores"].items():
            if dim in exempt_dims:
                assert entry["score"] == 1.0
            else:
                assert entry["score"] == 0.0


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
