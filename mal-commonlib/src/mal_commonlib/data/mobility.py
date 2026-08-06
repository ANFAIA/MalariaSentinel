"""Gravity-model mobility OD matrix builder + CSR binary writer.

Builds row-stochastic sparse origin-destination matrices for the ABM
engine using a gravity model: P(i->j) ∝ H(j) * exp(-β * d(i,j)).

The output is a binary CSR file compatible with the C++
``SparseOD::load_from_csr()`` reader in mobility_schedule.hpp.
"""
from __future__ import annotations

import pathlib

import numpy as np
from scipy.signal import fftconvolve


# ---------------------------------------------------------------------------
# Gravity model
# ---------------------------------------------------------------------------

def build_gravity_od(
    attractiveness: np.ndarray,
    cell_size_km: float,
    beta: float,
    max_distance_km: float = 50.0,
    sparsity_threshold: float = 5e-4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """Build a row-stochastic sparse OD matrix from a gravity model.

    For each origin cell i the probability of moving to destination cell j is::

        P(i->j) ∝ H(j) × exp(-β × d(i,j))

    where H(j) is the attractiveness of j and d(i,j) is the Euclidean
    distance between cell centres in km.

    Rows are normalised so that Σ_j P(i->j) = 1, then entries with
    P < *sparsity_threshold* are dropped and the kept entries are
    renormalised so each row sums to 1.0 again (the C++ reader
    validates row sums within ±0.01).

    Implementation: the grid is regular, so d(i,j) depends only on the
    offset (Δr, Δc).  Row sums are computed with one FFT convolution and
    entries are enumerated offset-by-offset with vectorised numpy ops —
    O(K·N) with K = number of offsets inside the distance disk.  No dense
    N×N matrix is ever materialised; peak memory is O(nnz + N).

    Args:
        attractiveness: (H, W) array — destination attractiveness
            (e.g. population for humans, livestock count for animals).
            Negative / non-finite values (nodata) are treated as 0.
        cell_size_km: side length of each grid cell in km.
        beta: friction parameter — higher values keep people closer to home.
        max_distance_km: hard distance cutoff; cells beyond this are excluded.
        sparsity_threshold: minimum normalised probability to keep an entry.

    Returns:
        ``(row_ptr, col_idx, values, n_rows, n_cols)`` — CSR arrays where
        each row sums to ~1.0, compatible with ``SparseOD::load_from_csr()``.
    """
    grid = np.asarray(attractiveness, dtype=np.float64)
    if grid.ndim != 2:
        raise ValueError(f"attractiveness must be 2D, got shape {grid.shape}")
    n_rows_grid, n_cols_grid = grid.shape
    n_cells = n_rows_grid * n_cols_grid

    grid = np.where(np.isfinite(grid) & (grid > 0.0), grid, 0.0)

    # --- Distance kernel over the offset disk ------------------------------
    radius_cells = int(max_distance_km // cell_size_km)
    ax = np.arange(-radius_cells, radius_cells + 1)
    dr_2d, dc_2d = np.meshgrid(ax, ax, indexing="ij")
    dist = np.hypot(dr_2d, dc_2d) * cell_size_km
    in_disk = dist <= max_distance_km
    kernel = np.exp(-beta * dist)
    kernel[~in_disk] = 0.0

    offsets = np.argwhere(in_disk) - radius_cells  # (K, 2) rows of (dr, dc)
    kern_vals = kernel[in_disk]

    # --- Row sums over all pairs within the disk (symmetric kernel) --------
    row_sums = fftconvolve(grid, kernel, mode="same")

    # --- Pass 1: per-row kept-entry counts + kept probability mass ---------
    counts = np.zeros((n_rows_grid, n_cols_grid), dtype=np.int64)
    kept_mass = np.zeros((n_rows_grid, n_cols_grid), dtype=np.float64)

    for (a, b), k in zip(offsets, kern_vals):
        r0, r1 = max(0, -a), n_rows_grid - max(0, a)
        c0, c1 = max(0, -b), n_cols_grid - max(0, b)
        if r0 >= r1 or c0 >= c1:
            continue  # offset larger than the grid itself
        dest = grid[r0 + a:r1 + a, c0 + b:c1 + b]
        rs = row_sums[r0:r1, c0:c1]
        p = (k * dest) / np.where(rs > 0.0, rs, 1.0)
        m = p > 0.0 if sparsity_threshold <= 0.0 else p >= sparsity_threshold
        counts[r0:r1, c0:c1] += m
        kept_mass[r0:r1, c0:c1] += np.where(m, p, 0.0)

    # --- Row pointers; empty rows get an identity (stay-home) entry --------
    counts_flat = counts.ravel().copy()
    empty = counts_flat == 0
    counts_flat[empty] = 1

    nnz = int(counts_flat.sum())
    row_ptr = np.empty(n_cells + 1, dtype=np.int32)
    row_ptr[0] = 0
    np.cumsum(counts_flat, dtype=np.int32, out=row_ptr[1:])

    # --- Pass 2: fill col_idx / values (recompute masks, no big temporaries)
    col_idx = np.empty(nnz, dtype=np.int32)
    values = np.empty(nnz, dtype=np.float32)
    cursor = row_ptr[:-1].astype(np.int64)
    kept_flat = kept_mass.ravel()

    if empty.any():
        eidx = np.flatnonzero(empty)
        pos = cursor[eidx]
        col_idx[pos] = eidx.astype(np.int32)
        values[pos] = 1.0
        cursor[eidx] += 1

    for (a, b), k in zip(offsets, kern_vals):
        r0, r1 = max(0, -a), n_rows_grid - max(0, a)
        c0, c1 = max(0, -b), n_cols_grid - max(0, b)
        if r0 >= r1 or c0 >= c1:
            continue  # offset larger than the grid itself
        width = c1 - c0
        dest = grid[r0 + a:r1 + a, c0 + b:c1 + b]
        rs = row_sums[r0:r1, c0:c1]
        p = (k * dest) / np.where(rs > 0.0, rs, 1.0)
        m = p > 0.0 if sparsity_threshold <= 0.0 else p >= sparsity_threshold
        loc = np.flatnonzero(m.ravel())
        if loc.size == 0:
            continue
        lr, lc = np.divmod(loc, width)
        origin = (r0 + lr) * n_cols_grid + (c0 + lc)
        pos = cursor[origin]
        col_idx[pos] = ((r0 + a + lr) * n_cols_grid + (c0 + b + lc)).astype(np.int32)
        values[pos] = (p.ravel()[loc] / kept_flat[origin]).astype(np.float32)
        cursor[origin] += 1

    if not np.array_equal(cursor, row_ptr[1:].astype(np.int64)):
        raise RuntimeError("build_gravity_od: CSR fill cursor mismatch")

    return row_ptr, col_idx, values, n_cells, n_cells


def build_identity_od(n_cells: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """Build an identity OD matrix (everyone stays home)."""
    row_ptr = np.arange(n_cells + 1, dtype=np.int32)
    col_idx = np.arange(n_cells, dtype=np.int32)
    values = np.ones(n_cells, dtype=np.float32)
    return row_ptr, col_idx, values, n_cells, n_cells


# ---------------------------------------------------------------------------
# CSR binary writer
# ---------------------------------------------------------------------------

def write_csr(
    row_ptr: np.ndarray,
    col_idx: np.ndarray,
    values: np.ndarray,
    n_rows: int,
    n_cols: int,
    path: pathlib.Path,
) -> pathlib.Path:
    """Write a sparse OD matrix in CSR binary format.

    Format (all little-endian, matching ``SparseOD::load_from_csr``)::

        [int32]  n_rows
        [int32]  n_cols
        [int32]  nnz
        [int32 × (n_rows+1)]  row_ptr
        [int32 × nnz]          col_idx
        [float32 × nnz]        values

    Returns:
        The path that was written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    nnz = col_idx.shape[0]

    with open(path, "wb") as f:
        f.write(np.int32(n_rows).tobytes())
        f.write(np.int32(n_cols).tobytes())
        f.write(np.int32(nnz).tobytes())
        f.write(row_ptr.astype(np.int32).tobytes())
        f.write(col_idx.astype(np.int32).tobytes())
        f.write(values.astype(np.float32).tobytes())

    return path
