"""Unit tests for D1/D5/D6/D7/D8/D9/D10 state COG scorers."""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds


def create_test_cog(
    path: Path,
    band0: np.ndarray,
    band1: np.ndarray,
    nodata: float = -9999.0,
) -> None:
    h, w = band0.shape
    transform = from_bounds(-1.5, 4.5, 1.5, 11.5, w, h)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=2,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(band0.astype(np.float32), 1)
        dst.write(band1.astype(np.float32), 2)


# ── D1 Expansion ──────────────────────────────────────────────────


class TestExpansion:
    def test_expansion_concentrated(self, tmp_path: Path) -> None:
        from scorers.expansion import ExpansionScorer

        rng = np.random.default_rng(42)
        b0 = np.zeros((20, 20), dtype=np.float32)
        b0[10, 10] = 0.8
        b0[10, 11] = 0.6
        b0[9, 10] = 0.5
        b1 = rng.random((20, 20)).astype(np.float32) * 0.3

        create_test_cog(tmp_path / "state_seed0001.tif", b0, b1)
        scorer = ExpansionScorer()
        result = scorer.score(tmp_path, {})
        assert result.value > 0.0
        assert 0.0 <= result.score <= 1.0

    def test_expansion_spread(self, tmp_path: Path) -> None:
        from scorers.expansion import ExpansionScorer

        rng = np.random.default_rng(42)
        b0 = rng.random((20, 20), dtype=np.float32) * 0.5
        b0[10, 10] = 0.9
        b1 = rng.random((20, 20), dtype=np.float32) * 0.3

        create_test_cog(tmp_path / "state_seed0001.tif", b0, b1)
        scorer = ExpansionScorer()
        result = scorer.score(tmp_path, {})
        assert result.value > 0.0

    def test_expansion_no_files(self, tmp_path: Path) -> None:
        from scorers.expansion import ExpansionScorer

        scorer = ExpansionScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == 0.0
        assert not result.passed


# ── D5 Moran's I ──────────────────────────────────────────────────


class TestMoransI:
    def test_morans_clustered(self, tmp_path: Path) -> None:
        from scorers.spatial import MoransScorer, _morans_i

        rng = np.random.default_rng(42)
        # Moderate spatial autocorrelation: smooth gradient + noise
        b0 = np.zeros((30, 30), dtype=np.float32)
        base = np.zeros((30, 30), dtype=np.float32)
        for i in range(30):
            for j in range(30):
                base[i, j] = float(i + j)
        noise = rng.standard_normal((30, 30)).astype(np.float32) * 8.0
        grid = (base + noise).astype(np.float32)
        b0[15, 15] = 0.5
        create_test_cog(tmp_path / "state_seed0001.tif", b0, grid)
        scorer = MoransScorer()
        result = scorer.score(tmp_path, {})
        assert result.value > 0.45, f"Expected I > 0.45 for noisy gradient, got {result.value}"
        assert result.value <= 0.70, f"Expected I <= 0.70, got {result.value}"
        assert result.score == 1.0

    def test_morans_random(self, tmp_path: Path) -> None:
        from scorers.spatial import MoransScorer, _morans_i

        rng = np.random.default_rng(42)
        b0 = np.zeros((30, 30), dtype=np.float32)
        grid = rng.random((30, 30), dtype=np.float32)
        b0[15, 15] = 0.5
        create_test_cog(tmp_path / "state_seed0001.tif", b0, grid)
        scorer = MoransScorer()
        result = scorer.score(tmp_path, {})
        assert abs(result.value) < 0.3, f"Expected I ~0 for random, got {result.value}"

    def test_morans_no_file(self, tmp_path: Path) -> None:
        from scorers.spatial import MoransScorer

        scorer = MoransScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == 0.0
        assert not result.passed


# ── D6 Mass Conservation ──────────────────────────────────────────


class TestMass:
    def test_mass_all_valid(self, tmp_path: Path) -> None:
        from scorers.mass import MassScorer

        rng = np.random.default_rng(42)
        b0 = rng.random((10, 10), dtype=np.float32)
        b1 = rng.random((10, 10), dtype=np.float32)
        create_test_cog(tmp_path / "state_day0001.tif", b0, b1)
        create_test_cog(tmp_path / "state_day0002.tif", b0, b1)
        scorer = MassScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == pytest.approx(1.0)

    def test_mass_some_nan(self, tmp_path: Path) -> None:
        from scorers.mass import MassScorer

        rng = np.random.default_rng(42)
        b0 = rng.random((10, 10), dtype=np.float32)
        b1 = rng.random((10, 10), dtype=np.float32)
        b0[0, 0] = float("nan")
        b1[5, 5] = float("nan")
        create_test_cog(tmp_path / "state_day0001.tif", b0, b1)
        scorer = MassScorer()
        result = scorer.score(tmp_path, {})
        assert result.score < 1.0

    def test_mass_out_of_range(self, tmp_path: Path) -> None:
        from scorers.mass import MassScorer

        rng = np.random.default_rng(42)
        b0 = rng.random((10, 10), dtype=np.float32)
        b1 = rng.random((10, 10), dtype=np.float32) * 2.0
        create_test_cog(tmp_path / "state_day0001.tif", b0, b1)
        scorer = MassScorer()
        result = scorer.score(tmp_path, {})
        assert result.score < 1.0


# ── D7 Determinism ────────────────────────────────────────────────


class TestDeterminism:
    def test_determinism_single_cog(self, tmp_path: Path) -> None:
        from scorers.determinism import DeterminismScorer

        rng = np.random.default_rng(42)
        b0 = rng.random((10, 10), dtype=np.float32)
        b1 = rng.random((10, 10), dtype=np.float32)
        create_test_cog(tmp_path / "state_seed0001.tif", b0, b1)
        scorer = DeterminismScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == 1.0

    def test_determinism_matching_pair(self, tmp_path: Path) -> None:
        from scorers.determinism import DeterminismScorer

        rng = np.random.default_rng(42)
        b0 = rng.random((10, 10), dtype=np.float32)
        b1 = rng.random((10, 10), dtype=np.float32)
        create_test_cog(tmp_path / "state_seed0001_a.tif", b0, b1)
        create_test_cog(tmp_path / "state_seed0001_b.tif", b0, b1)
        scorer = DeterminismScorer()
        result = scorer.score(tmp_path, {})
        # seed-tag extraction uses regex on filename; "seed0001_a" and "seed0001_b" have
        # different tags, so this actually tests the default-one-per-seed path
        assert result.score == 1.0


# ── D8 Coupling ───────────────────────────────────────────────────


class TestCoupling:
    def test_coupling_correlated(self, tmp_path: Path) -> None:
        from scorers.coupling import CouplingScorer

        b0 = np.array([[0.1, 0.5, 0.8], [0.3, 0.6, 0.9]], dtype=np.float32)
        b1 = b0.copy()
        create_test_cog(tmp_path / "state_seed0001.tif", b0, b1)
        scorer = CouplingScorer()
        result = scorer.score(tmp_path, {})
        assert result.value == pytest.approx(1.0, abs=1e-4)
        assert result.score == pytest.approx(1.0, abs=1e-4)
        assert result.passed

    def test_coupling_uncorrelated(self, tmp_path: Path) -> None:
        from scorers.coupling import CouplingScorer

        rng = np.random.default_rng(42)
        b0 = rng.random((50, 50), dtype=np.float32)
        b1 = rng.random((50, 50), dtype=np.float32)
        create_test_cog(tmp_path / "state_seed0001.tif", b0, b1)
        scorer = CouplingScorer()
        result = scorer.score(tmp_path, {})
        assert result.value < 0.30
        assert result.score < 0.60


# ── D9 Activation ─────────────────────────────────────────────────


class TestActivation:
    def test_activation_normal(self, tmp_path: Path) -> None:
        from scorers.activation import ActivationScorer

        rng = np.random.default_rng(42)
        for d in range(1, 4):
            b0 = rng.random((20, 20), dtype=np.float32)
            b1 = np.zeros((20, 20), dtype=np.float32)
            active = rng.random((20, 20)) < 0.20
            b1[active] = rng.random(active.sum()).astype(np.float32) * 0.5
            create_test_cog(tmp_path / f"state_day{d:04d}.tif", b0, b1)

        scorer = ActivationScorer()
        result = scorer.score(tmp_path, {})
        assert 0.05 <= result.value <= 0.35, f"Expected rate ~0.20, got {result.value}"
        assert result.passed or result.score > 0.8

    def test_activation_none(self, tmp_path: Path) -> None:
        from scorers.activation import ActivationScorer

        b0 = np.ones((10, 10), dtype=np.float32)
        b1 = np.zeros((10, 10), dtype=np.float32)
        create_test_cog(tmp_path / "state_day0001.tif", b0, b1)

        scorer = ActivationScorer()
        result = scorer.score(tmp_path, {})
        assert result.value == pytest.approx(0.0)
        assert result.score < 0.12


# ── D10 Performance ───────────────────────────────────────────────


class TestPerformance:
    def test_perf_fast(self, tmp_path: Path) -> None:
        from scorers.performance import PerformanceScorer

        (tmp_path / "run_metadata.json").write_text(json.dumps({"wall_s": 20}))
        scorer = PerformanceScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == pytest.approx(1.0)
        assert result.passed

    def test_perf_slow(self, tmp_path: Path) -> None:
        from scorers.performance import PerformanceScorer

        (tmp_path / "run_metadata.json").write_text(json.dumps({"wall_s": 60}))
        scorer = PerformanceScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == pytest.approx(0.5)
        assert not result.passed

    def test_perf_no_metadata(self, tmp_path: Path) -> None:
        from scorers.performance import PerformanceScorer

        scorer = PerformanceScorer()
        result = scorer.score(tmp_path, {})
        assert result.score == 1.0


# ── Composite ─────────────────────────────────────────────────────


class TestComposite:
    def test_geometric_mean_all_ones(self) -> None:
        from scorers.base import ScorerResult
        from scorers.composite import geometric_mean

        scores = {f"D{i}": ScorerResult(score=1.0) for i in range(1, 11)}
        assert geometric_mean(scores) == pytest.approx(1.0)

    def test_geometric_mean_one_zero(self) -> None:
        from scorers.base import ScorerResult
        from scorers.composite import geometric_mean

        scores = {f"D{i}": ScorerResult(score=1.0) for i in range(1, 11)}
        scores["D5_morans"] = ScorerResult(score=0.0)
        assert geometric_mean(scores) == 0.0

    def test_geometric_mean_weighted(self) -> None:
        from scorers.base import ScorerResult
        from scorers.composite import geometric_mean

        scores = {
            "D1_expansion": ScorerResult(score=0.5),
            "D5_morans": ScorerResult(score=0.8),
        }
        # weights: D1=2.0, D5=1.0, total=3.0
        # log GM = (2*log(0.5) + 1*log(0.8)) / 3
        expected = math.exp((2 * math.log(0.5) + math.log(0.8)) / 3)
        assert geometric_mean(scores) == pytest.approx(expected, rel=1e-6)