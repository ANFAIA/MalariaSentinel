"""Gravity-model mobility OD matrix builder + CSR binary writer.

Builds row-stochastic sparse origin-destination matrices for the ABM
engine using a gravity model: P(i->j) ∝ H(j) * exp(-β * d(i,j)).

The output is a binary CSR file compatible with the C++
``SparseOD::load_from_csr()`` reader in mobility_schedule.hpp.
"""
from __future__ import annotations

import pathlib

import numpy as np


# ---------------------------------------------------------------------------
# Gravity model
# ---------------------------------------------------------------------------

def build_gravity_od(
    attractiveness: np.ndarray,
    cell_size_km: float,
    beta: float,
    max_distance_km: float = 50.0,
    sparsity_threshold: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """Build a row-stochastic sparse OD matrix from a gravity model.

    For each origin cell i the probability of moving to destination cell j is::

        P(i->j) ∝ H(j) × exp(-β × d(i,j))

    where H(j) is the attractiveness of j and d(i,j) is the Euclidean
    distance between cell centres in km.

    Rows are normalised so that Σ_j P(i->j) = 1.  Cells with
    P < *sparsity_threshold* are dropped from the sparse representation.

    Args:
        attractiveness: (H, W) array — destination attractiveness
            (e.g. population for humans, livestock count for animals).
        cell_size_km: side length of each grid cell in km.
        beta: friction parameter — higher values keep people closer to home.
        max_distance_km: hard distance cutoff; cells beyond this are excluded.
        sparsity_threshold: minimum probability to keep an entry.

    Returns:
        ``(row_ptr, col_idx, values, n_rows, n_cols)`` — CSR arrays where
        each row sums to ~1.0, compatible with ``SparseOD::load_from_csr()``.
    """
    flat = attractiveness.ravel().astype(np.float64)
    n_cells = flat.shape[0]

    # Cell centre coordinates (row-major flattening)
    H, W = attractiveness.shape
    rows_2d, cols_2d = np.mgrid[0:H, 0:W]
    cx = cols_2d.ravel().astype(np.float64) * cell_size_km
    cy = rows_2d.ravel().astype(np.float64) * cell_size_km

    # Max distance in cell units for the per-row neighbourhood search
    max_cells = int(np.ceil(max_distance_km / cell_size_km))

    row_ptr = np.zeros(n_cells + 1, dtype=np.int32)
    col_indices: list[np.ndarray] = []
    value_list: list[np.ndarray] = []

    for i in range(n_cells):
        # Candidate destinations within a square bounding box
        ri, ci = int(cy[i] / cell_size_km), int(cx[i] / cell_size_km)
        r_lo = max(0, ri - max_cells)
        r_hi = min(H, ri + max_cells + 1)
        c_lo = max(0, ci - max_cells)
        c_hi = min(W, ci + max_cells + 1)

        # Flat indices of candidates
        rr, cc = np.mgrid[r_lo:r_hi, c_lo:c_hi]
        j_idx = (rr.ravel() * W + cc.ravel()).astype(np.int64)

        # Distances in km
        dx = cx[j_idx] - cx[i]
        dy = cy[j_idx] - cy[i]
        dist = np.sqrt(dx * dx + dy * dy)

        # Gravity score
        within = dist <= max_distance_km
        j_idx = j_idx[within]
        dist = dist[within]
        scores = flat[j_idx] * np.exp(-beta * dist)

        # Normalise
        total = scores.sum()
        if total > 0:
            probs = (scores / total).astype(np.float32)
            mask = probs >= sparsity_threshold
            j_idx = j_idx[mask].astype(np.int32)
            probs = probs[mask]
        else:
            # Empty row — stay at self (identity fallback)
            j_idx = np.array([i], dtype=np.int32)
            probs = np.array([1.0], dtype=np.float32)

        col_indices.append(j_idx)
        value_list.append(probs)
        row_ptr[i + 1] = row_ptr[i] + len(j_idx)

    nnz = row_ptr[-1]
    col_idx = np.concatenate(col_indices) if col_indices else np.array([], dtype=np.int32)
    values = np.concatenate(value_list) if value_list else np.array([], dtype=np.float32)

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
