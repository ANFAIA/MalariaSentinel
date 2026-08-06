"""Tests for gravity-model mobility OD builder + CSR writer.

Validates the vectorised offset implementation against a brute-force
reference on small grids, plus the binary CSR format contract expected
by the C++ ``SparseOD::load_from_csr()`` reader.
"""
from __future__ import annotations

import pathlib
import struct

import numpy as np
import pytest

from mal_commonlib.data.mobility import (
    build_gravity_od,
    build_identity_od,
    write_csr,
)


def _reference_gravity_od(
    grid: np.ndarray,
    cell_size_km: float,
    beta: float,
    max_distance_km: float,
    sparsity_threshold: float,
) -> dict[int, list[tuple[int, float]]]:
    """O(N^2) brute-force reference. Returns {row: [(col, prob), ...]}."""
    grid = np.where(np.isfinite(grid) & (grid > 0), grid, 0.0).astype(np.float64)
    H, W = grid.shape
    n = H * W
    flat = grid.ravel()
    coords = np.array([(r, c) for r in range(H) for c in range(W)], dtype=np.float64)

    out: dict[int, list[tuple[int, float]]] = {}
    for i in range(n):
        d = np.sqrt(((coords - coords[i]) ** 2).sum(axis=1)) * cell_size_km
        within = d <= max_distance_km
        scores = np.where(within, flat * np.exp(-beta * d), 0.0)
        total = scores.sum()
        if total <= 0:
            out[i] = [(i, 1.0)]
            continue
        probs = scores / total
        keep = probs >= sparsity_threshold
        if not keep.any():
            out[i] = [(i, 1.0)]
            continue
        kept = probs[keep]
        kept = kept / kept.sum()
        out[i] = [(int(j), float(p)) for j, p in zip(np.flatnonzero(keep), kept)]
    return out


def _csr_to_rows(
    row_ptr: np.ndarray, col_idx: np.ndarray, values: np.ndarray
) -> dict[int, list[tuple[int, float]]]:
    rows: dict[int, list[tuple[int, float]]] = {}
    for i in range(len(row_ptr) - 1):
        rows[i] = [
            (int(col_idx[k]), float(values[k]))
            for k in range(row_ptr[i], row_ptr[i + 1])
        ]
    return rows


def _assert_rows_equal(ref, got, atol=1e-5):
    assert set(ref.keys()) == set(got.keys())
    for i in ref:
        ref_cols = {c: p for c, p in ref[i]}
        got_cols = {c: p for c, p in got[i]}
        assert set(ref_cols) == set(got_cols), f"row {i}: col sets differ"
        for c in ref_cols:
            assert abs(ref_cols[c] - got_cols[c]) < atol, (
                f"row {i} col {c}: ref {ref_cols[c]} != got {got_cols[c]}"
            )


def test_matches_brute_force_small_grid():
    rng = np.random.default_rng(42)
    grid = rng.random((6, 7)) * 10
    grid[0, 0] = 0  # a couple of empty cells
    grid[5, 6] = 0

    rp, ci, vl, nr, nc = build_gravity_od(grid, 1.0, 0.3, 3.0, 0.01)
    assert nr == 42 and nc == 42

    ref = _reference_gravity_od(grid, 1.0, 0.3, 3.0, 0.01)
    _assert_rows_equal(ref, _csr_to_rows(rp, ci, vl))


def test_matches_brute_force_nodata():
    rng = np.random.default_rng(7)
    grid = rng.random((5, 5)) * 5
    grid[2, 2] = -9999.0  # nodata must behave as 0
    grid[0, :] = -9999.0

    rp, ci, vl, _, _ = build_gravity_od(grid, 1.0, 0.5, 2.5, 0.005)
    clean = np.where(grid == -9999.0, 0.0, grid)
    ref = _reference_gravity_od(clean, 1.0, 0.5, 2.5, 0.005)
    _assert_rows_equal(ref, _csr_to_rows(rp, ci, vl))


def test_row_sums_and_bounds():
    rng = np.random.default_rng(1)
    grid = rng.random((8, 9)) * 3
    rp, ci, vl, nr, nc = build_gravity_od(grid, 1.0, 0.2, 4.0, 1e-3)

    assert rp.dtype == np.int32 and ci.dtype == np.int32 and vl.dtype == np.float32
    assert len(rp) == nr + 1 and rp[0] == 0 and rp[-1] == len(ci)
    assert np.all(np.diff(rp) >= 0)
    assert np.all(ci >= 0) and np.all(ci < nc)

    rows = _csr_to_rows(rp, ci, vl)
    for i, entries in rows.items():
        assert len(entries) > 0, f"row {i} empty"
        s = sum(p for _, p in entries)
        assert abs(s - 1.0) < 1e-3, f"row {i} sums to {s}"


def test_all_zero_grid_is_identity():
    grid = np.zeros((4, 4))
    rp, ci, vl, nr, nc = build_gravity_od(grid, 1.0, 0.1, 5.0, 1e-3)
    rows = _csr_to_rows(rp, ci, vl)
    for i in range(nr):
        assert rows[i] == [(i, 1.0)]


def test_cell_size_scaling():
    # Doubling cell_size doubles physical distances; halving beta (per-km)
    # and doubling max_distance keeps the kernel identical in cell units.
    rng = np.random.default_rng(3)
    grid = rng.random((5, 6)) * 4
    rp1, ci1, vl1, _, _ = build_gravity_od(grid, 1.0, 0.4, 2.0, 1e-4)
    rp2, ci2, vl2, _, _ = build_gravity_od(grid, 2.0, 0.2, 4.0, 1e-4)
    assert np.array_equal(rp1, rp2) and np.array_equal(ci1, ci2)
    assert np.allclose(vl1, vl2, atol=1e-5)


def test_identity_od():
    rp, ci, vl, nr, nc = build_identity_od(10)
    assert nr == nc == 10
    assert np.array_equal(rp, np.arange(11, dtype=np.int32))
    assert np.array_equal(ci, np.arange(10, dtype=np.int32))
    assert np.all(vl == 1.0)


def _read_csr_binary(path: pathlib.Path):
    """Parse the binary format exactly like SparseOD::load_from_csr."""
    with open(path, "rb") as f:
        blob = f.read()
    nr, nc, nnz = struct.unpack_from("<iii", blob, 0)
    off = 12
    rp = np.frombuffer(blob, dtype="<i4", count=nr + 1, offset=off)
    off += 4 * (nr + 1)
    ci = np.frombuffer(blob, dtype="<i4", count=nnz, offset=off)
    off += 4 * nnz
    vl = np.frombuffer(blob, dtype="<f4", count=nnz, offset=off)
    off += 4 * nnz
    assert off == len(blob), "trailing bytes in CSR file"
    return nr, nc, nnz, rp, ci, vl


def test_write_csr_binary_format(tmp_path):
    rng = np.random.default_rng(5)
    grid = rng.random((6, 6)) * 8
    rp, ci, vl, nr, nc = build_gravity_od(grid, 1.0, 0.25, 3.0, 1e-3)
    p = write_csr(rp, ci, vl, nr, nc, tmp_path / "test.csr")

    nr2, nc2, nnz2, rp2, ci2, vl2 = _read_csr_binary(p)
    assert (nr2, nc2) == (nr, nc)
    assert nnz2 == len(ci)
    assert np.array_equal(rp2, rp)
    assert np.array_equal(ci2, ci)
    assert np.allclose(vl2, vl)

    # C++ validate() contract: row sums within ±0.01, col_idx in bounds
    assert np.all(ci2 >= 0) and np.all(ci2 < nc2)
    for r in range(nr2):
        s = float(vl2[rp2[r]:rp2[r + 1]].sum())
        if rp2[r + 1] > rp2[r]:
            assert abs(s - 1.0) <= 0.01, f"row {r} sum {s} outside C++ tolerance"
