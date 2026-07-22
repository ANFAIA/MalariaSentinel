"""Unit tests for D2 (mortality), D3 (EIP), D4 (stability) cohort scorers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scorers.mortality import MortalityScorer
from scorers.eip import EIPScorer
from scorers.stability import StabilityScorer


def _write_cohort(path: Path, daily: list[dict]) -> None:
    path.write_text(json.dumps({"n_days": len(daily), "daily": daily}))


# ---------------------------------------------------------------------------
# D2: Mortality scorer
# ---------------------------------------------------------------------------

class TestMortalityScorer:
    def test_perfect(self, tmp_path: Path) -> None:
        """p_d=0.915 -> mean life ~11.8d -> score close to 1.0."""
        daily = []
        n_adults = 500
        for d in range(90):
            n_deaths = int(n_adults * 0.085)  # p_d = 0.915
            daily.append({"day": d, "n_adults": n_adults, "n_deaths": n_deaths,
                          "n_alive": n_adults, "n_larvae": 0, "n_births": 0,
                          "n_maturation": 0, "eip_frac": 0.3})
        _write_cohort(tmp_path / "cohort.json", daily)
        scorer = MortalityScorer()
        result = scorer.score(tmp_path, {})
        assert result.score >= 0.80, f"Expected >= 0.80, got {result.score}"
        assert result.passed is True

    def test_collapsed(self, tmp_path: Path) -> None:
        """p_d=0.82 -> mean life ~5.6d -> score < 0.30."""
        daily = []
        n_adults = 500
        for d in range(90):
            n_deaths = int(n_adults * 0.18)  # p_d = 0.82
            daily.append({"day": d, "n_adults": n_adults, "n_deaths": n_deaths,
                          "n_alive": n_adults, "n_larvae": 0, "n_births": 0,
                          "n_maturation": 0, "eip_frac": 0.3})
        _write_cohort(tmp_path / "cohort.json", daily)
        scorer = MortalityScorer()
        result = scorer.score(tmp_path, {})
        assert result.score < 0.30, f"Expected < 0.30, got {result.score}"
        assert result.passed is False

    def test_missing_file(self, tmp_path: Path) -> None:
        """No cohort.json -> score=0.0."""
        scorer = MortalityScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == 0.0
        assert result.passed is False


# ---------------------------------------------------------------------------
# D3: EIP scorer
# ---------------------------------------------------------------------------

class TestEIPScorer:
    def test_in_range(self, tmp_path: Path) -> None:
        """eip_frac=0.35 at day 30 -> score=1.0."""
        daily = []
        for d in range(90):
            daily.append({"day": d, "n_adults": 200, "n_deaths": 10,
                          "n_alive": 5000, "n_larvae": 3000, "n_births": 50,
                          "n_maturation": 5, "eip_frac": 0.35 if d == 30 else 0.3})
        _write_cohort(tmp_path / "cohort.json", daily)
        scorer = EIPScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == 1.0
        assert result.passed is True

    def test_below_range(self, tmp_path: Path) -> None:
        """eip_frac=0.05 -> score < 0.30."""
        daily = []
        for d in range(90):
            daily.append({"day": d, "n_adults": 200, "n_deaths": 10,
                          "n_alive": 5000, "n_larvae": 3000, "n_births": 50,
                          "n_maturation": 5, "eip_frac": 0.05 if d == 30 else 0.05})
        _write_cohort(tmp_path / "cohort.json", daily)
        scorer = EIPScorer()
        result = scorer.score(tmp_path, {})
        assert result.score < 0.30, f"Expected < 0.30, got {result.score}"

    def test_above_range(self, tmp_path: Path) -> None:
        """eip_frac=0.70 -> score < 0.30."""
        daily = []
        for d in range(90):
            daily.append({"day": d, "n_adults": 200, "n_deaths": 10,
                          "n_alive": 5000, "n_larvae": 3000, "n_births": 50,
                          "n_maturation": 5, "eip_frac": 0.70 if d == 30 else 0.3})
        _write_cohort(tmp_path / "cohort.json", daily)
        scorer = EIPScorer()
        result = scorer.score(tmp_path, {})
        assert result.score < 0.30, f"Expected < 0.30, got {result.score}"


# ---------------------------------------------------------------------------
# D4: Stability scorer
# ---------------------------------------------------------------------------

class TestStabilityScorer:
    def test_healthy(self, tmp_path: Path) -> None:
        """collapse_ratio=0.5, explosion_ratio=2.0 -> score=1.0."""
        daily = []
        # day 0: 1000, day 30: 500, day 60: 600, day 90: 700
        pops = [1000] * 30 + [500] * 30 + [600] * 30
        for d in range(90):
            daily.append({"day": d, "n_alive": pops[d], "n_adults": 100,
                          "n_deaths": 5, "n_larvae": 0, "n_births": 0,
                          "n_maturation": 0, "eip_frac": 0.3})
        _write_cohort(tmp_path / "cohort.json", daily)
        scorer = StabilityScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == 1.0, f"Expected 1.0, got {result.score}"
        assert result.passed is True

    def test_collapse(self, tmp_path: Path) -> None:
        """collapse_ratio=0.05 with explosion -> score penalised."""
        daily = []
        # day 0: 1000, day 30: 50 (5%), day 60: 50, day 90: 50
        # Also spike to 8000 (8x) at day 45 to trigger explosion penalty
        pops = [1000] * 30 + [50] * 15 + [8000] + [50] * 44
        for d in range(90):
            daily.append({"day": d, "n_alive": pops[d], "n_adults": 100,
                          "n_deaths": 5, "n_larvae": 0, "n_births": 0,
                          "n_maturation": 0, "eip_frac": 0.3})
        _write_cohort(tmp_path / "cohort.json", daily)
        scorer = StabilityScorer()
        result = scorer.score(tmp_path, {})
        # With collapse_ratio=0.05 and explosion_ratio=8.0,
        # collapse_ok~0.78 and explosion_ok~0.697 -> avg~0.74
        assert result.score < 0.80, f"Expected < 0.80, got {result.score}"
        assert result.diagnostics["explosion_ratio"] > 5.0

    def test_explosion(self, tmp_path: Path) -> None:
        """explosion_ratio=10.0 -> score < 0.70."""
        daily = []
        # day 0: 1000, day 30-90: stable but max is 10000 at some point
        for d in range(90):
            n_alive = 10000 if d == 45 else 1000
            daily.append({"day": d, "n_alive": n_alive, "n_adults": 100,
                          "n_deaths": 5, "n_larvae": 0, "n_births": 0,
                          "n_maturation": 0, "eip_frac": 0.3})
        _write_cohort(tmp_path / "cohort.json", daily)
        scorer = StabilityScorer()
        result = scorer.score(tmp_path, {})
        assert result.score < 0.70, f"Expected < 0.70, got {result.score}"
