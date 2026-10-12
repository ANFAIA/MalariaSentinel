"""Unit tests for canon state-COG scorers and gates: D5 Moran's I,
D8 coupling, G7 determinism, G10 performance.

Adapted from the calibration harness tests (2026-10) with the canon
semantics: missing artifacts -> ``status="skipped"``; determinism and
performance are GATEs now, not composite dimensions.
"""
from __future__ import annotations

import json
from numbers import Number
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

from mal_core.scoring.scorers.d5_morans import MoransScorer
from mal_core.scoring.scorers.d8_coupling import CouplingScorer
from mal_core.scoring.scorers.gates import DeterminismGate, PerformanceGate


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


# ---------------------------------------------------------------------------
# D5: Moran's I (spatial autocorrelation of active/band-1 cells)
# ---------------------------------------------------------------------------

class TestMoransI:
    def test_morans_clustered(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(42)
        # Smooth noisy gradient -> moderate spatial autocorrelation.
        base = np.add.outer(np.arange(30), np.arange(30)).astype(np.float32)
        noise = rng.standard_normal((30, 30)).astype(np.float32) * 8.0
        gradient = (base + noise).astype(np.float32)
        gradient = np.clip(gradient, 0, None)  # band-1 active cells are > 0
        create_test_cog(tmp_path / "state_seed0001.tif", gradient, gradient)
        scorer = MoransScorer()
        result = scorer.score(tmp_path, {})
        assert result.value > 0.45, f"Expected I > 0.45 for noisy gradient, got {result.value}"
        assert result.value <= 0.70, f"Expected I <= 0.70, got {result.value}"
        assert result.score == 1.0

    def test_morans_random(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(42)
        grid = rng.random((30, 30), dtype=np.float32)
        create_test_cog(tmp_path / "state_seed0001.tif", grid, grid)
        scorer = MoransScorer()
        result = scorer.score(tmp_path, {})
        assert abs(result.value) < 0.3, f"Expected I ~0 for random, got {result.value}"

    def test_morans_no_file(self, tmp_path: Path) -> None:
        scorer = MoransScorer()
        result = scorer.score(tmp_path, {})
        assert result.status == "skipped"
        assert result.score == 0.0
        assert not result.passed


# ---------------------------------------------------------------------------
# D8: Coupling (density vs habitat pressure correlation)
# ---------------------------------------------------------------------------

class TestCoupling:
    def test_coupling_correlated(self, tmp_path: Path) -> None:
        b0 = np.array([[0.1, 0.5, 0.8], [0.3, 0.6, 0.9]], dtype=np.float32)
        b1 = b0.copy()
        create_test_cog(tmp_path / "state_seed0001.tif", b0, b1)
        scorer = CouplingScorer()
        result = scorer.score(tmp_path, {})
        assert result.value == pytest.approx(1.0, abs=1e-4)
        assert result.score == pytest.approx(1.0, abs=1e-4)
        assert result.passed

    def test_coupling_uncorrelated(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(42)
        b0 = rng.random((50, 50), dtype=np.float32)
        b1 = rng.random((50, 50), dtype=np.float32)
        create_test_cog(tmp_path / "state_seed0001.tif", b0, b1)
        scorer = CouplingScorer()
        result = scorer.score(tmp_path, {})
        assert result.value < 0.30
        assert result.score < 0.60

    def test_coupling_no_file(self, tmp_path: Path) -> None:
        scorer = CouplingScorer()
        result = scorer.score(tmp_path, {})
        assert result.status == "skipped"
        assert not result.passed


# ---------------------------------------------------------------------------
# G7: Determinism gate (same-seed outputs byte-identical)
# ---------------------------------------------------------------------------

class TestDeterminismGate:
    def _write(self, path: Path, value: float = 0.5) -> None:
        create_test_cog(
            path,
            np.full((8, 8), value, dtype=np.float32),
            np.full((8, 8), value, dtype=np.float32),
        )

    def test_identical_pair_passes(self, tmp_path: Path) -> None:
        # Two byte-identical files in the same seed group.
        self._write(tmp_path / "state_seed0001.tif")
        self._write(tmp_path / "state_seed0001c.tif")
        scorer = DeterminismGate()
        result = scorer.score(tmp_path, {})
        assert result.score == 1.0
        assert result.passed is True

    def test_mismatch_pair_fails(self, tmp_path: Path) -> None:
        self._write(tmp_path / "state_seed0001.tif", value=0.5)
        self._write(tmp_path / "state_seed0001c.tif", value=0.9)
        scorer = DeterminismGate()
        result = scorer.score(tmp_path, {})
        assert result.score == 0.0
        assert result.passed is False

    def test_no_seed_files_skipped(self, tmp_path: Path) -> None:
        scorer = DeterminismGate()
        result = scorer.score(tmp_path, {})
        assert result.status == "skipped"


# ---------------------------------------------------------------------------
# G10: Performance gate (wall time from run_metadata.json)
# ---------------------------------------------------------------------------

class TestPerformanceGate:
    def test_perf_fast(self, tmp_path: Path) -> None:
        (tmp_path / "run_metadata.json").write_text(json.dumps({"wall_s": 20}))
        scorer = PerformanceGate()
        result = scorer.score(tmp_path, {})
        assert result.score == pytest.approx(1.0)
        assert result.passed

    def test_perf_slow(self, tmp_path: Path) -> None:
        (tmp_path / "run_metadata.json").write_text(json.dumps({"wall_s": 60}))
        scorer = PerformanceGate()
        result = scorer.score(tmp_path, {})
        assert result.score == pytest.approx(0.5)
        assert not result.passed

    def test_perf_no_metadata_skipped(self, tmp_path: Path) -> None:
        scorer = PerformanceGate()
        result = scorer.score(tmp_path, {})
        assert result.status == "skipped"
        assert isinstance(result.score, Number)
