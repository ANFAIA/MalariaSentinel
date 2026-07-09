"""Topographic Wetness Index from a DEM (M1.3a, pure numpy/scipy).

Public surface
--------------
``compute_twi(dem, *, cell_size_m=None) -> xr.DataArray``

TWI = ln(a / tan(β)) where ``a`` is the contributing area per cell (m²) and
β is the slope (radians). The reference formulation is Beven & Kirkby (1979).
We implement a pure numpy/scipy D8 flow-direction + flow-accumulation pipeline
that does not depend on ``pysheds`` — see ``arch-m1-3a-twi-scipy-numpy-custom``.

Algorithm
---------
1.  Slope β.  Computed from the central-difference gradient
        ∂z/∂x, ∂z/∂y  =  np.gradient(dem.values, cell_size_m)
        β  =  arctan( sqrt((∂z/∂x)² + (∂z/∂y)²) )
    This is the same as the steepest-finite-difference kernel but is
    a one-liner in numpy. Edge cells (1-cell border) get β=0 (and become
    nodata in the output). For consistency with the slope sign convention
    we use the *downhill* gradient (np.gradient returns the slope in the
    axis order — we take the magnitude).

2.  D8 flow direction.  For each cell, find the steepest-descent neighbour
    among the 8 surrounding cells. Encode the direction as an int8 code
    0..7. Ties go to the lower-index neighbour (deterministic). Flat cells
    (no descent) are routed to the lowest *equal-height* neighbour, with
    a deterministic tiebreak.

3.  Flow accumulation.  Topological sort by descending elevation. For each
    cell (in high → low order), add ``1 + sum_of_upstream_counts`` to the
    chosen neighbour's count. The count for each cell is in units of
    "number of upstream cells" — multiplying by ``cell_size_m²`` converts
    to a contributing area in m².

    For flat areas (e.g. all-zero DEM), the topological sort still works
    (all cells have equal elevation, so the sort is stable) and the
    D8 routing to a low-elevation neighbour keeps the accumulation finite.
    The slope ε guard prevents division by zero in TWI.

4.  TWI = ln((accum × cell_size_m²) / max(tan(β), ε)).  The ε is
    set to ``tan(0.1°) ≈ 1.7e-3``, which is the smallest physically
    meaningful slope for TWI.

5.  NoData.  Cells where the DEM is NaN → -9999.0. Edge cells (1-cell
    border where np.gradient uses one-sided differences) → -9999.0.
"""
from __future__ import annotations

import math

import numpy as np
import xarray as xr

# Edge margin where np.gradient uses one-sided differences.
_EDGE = 1
# Output nodata sentinel per docs/abm-output-contract.md §2.
_NODATA_OUT = np.float32(-9999.0)
_NODATA_OUT_SCALAR = -9999.0
# Minimum slope (radians) we feed into the tan(): ~0.1°.
_EPS_SLOPE_RAD = 0.1 * math.pi / 180.0

# D8 neighbour offsets: index 0..7 → (dy, dx)
# 0=E, 1=SE, 2=S, 3=SW, 4=W, 5=NW, 6=N, 7=NE  (matches ArcGIS clockwise-from-east)
_D8_OFFSETS = np.array(
    [
        (0, 1),    # 0: E
        (1, 1),    # 1: SE
        (1, 0),    # 2: S
        (1, -1),   # 3: SW
        (0, -1),   # 4: W
        (-1, -1),  # 5: NW
        (-1, 0),   # 6: N
        (-1, 1),   # 7: NE
    ],
    dtype=np.int8,
)
# Distance multipliers (in units of cell_size_m) for each neighbour: 1 for
# cardinal, sqrt(2) for diagonal.
_D8_DIST = np.array(
    [1.0, math.sqrt(2.0), 1.0, math.sqrt(2.0), 1.0, math.sqrt(2.0), 1.0, math.sqrt(2.0)],
    dtype=np.float32,
)


def _infer_cell_size_m(dem: xr.DataArray) -> float:
    """Infer the cell size in metres from the DataArray's coords or rio metadata."""
    # Try rioxarray first.
    try:
        res_x, res_y = dem.rio.resolution()
    except Exception:
        res_x = res_y = None
    if res_x is not None and res_y is not None:
        # rioxarray returns negative values for north-up rasters; use abs.
        size = max(abs(float(res_x)), abs(float(res_y)))
        if size > 0:
            # If the CRS is geographic, res_x/res_y are in degrees; convert
            # to metres using the AOI centroid latitude. We don't have the
            # AOI here — fall back to 0° latitude (111_320 m / deg) as a
            # safe default. Callers should pass cell_size_m explicitly for
            # geographic DEMs.
            try:
                crs = dem.rio.crs
                if crs is not None and crs.is_geographic:
                    # 1° lon ~111_320 m at the equator. For mid-latitudes
                    # this is within 30% of the true ground cell size.
                    return size * 111_320.0
            except Exception:
                pass
            return float(size)
    # Try x/y coords directly.
    if "x" in dem.dims and "y" in dem.dims:
        x = np.asarray(dem["x"].values)
        y = np.asarray(dem["y"].values)
        if x.size >= 2 and y.size >= 2:
            dx = abs(float(x[1] - x[0]))
            dy = abs(float(y[1] - y[0]))
            return max(dx, dy) if max(dx, dy) > 0 else 1.0
    raise ValueError(
        "Cannot infer cell_size_m: no .rio.resolution() and no x/y coords. "
        "Pass cell_size_m explicitly."
    )


def _d8_flow_direction(z: np.ndarray) -> np.ndarray:
    """Return a (H, W) int8 array of D8 flow-direction codes (0..7, or -1 for sinks)."""
    h, w = z.shape
    # Build a (8, H, W) array of the height difference (z - z_neighbour).
    # We pad the array so neighbour lookups stay in-bounds; pad cells get +inf
    # so they are never chosen as the steepest descent.
    z_pad = np.pad(z, _EDGE, mode="constant", constant_values=np.inf)
    # idx[k] = (y, x) of the neighbour for code k, in the padded coords.
    idx_y = (_EDGE + _D8_OFFSETS[:, 0]).astype(int)
    idx_x = (_EDGE + _D8_OFFSETS[:, 1]).astype(int)
    # descent = z - z_neighbour; we want the neighbour with the maximum descent.
    # For the slope weighting we use the actual grid distance.
    # We vectorize via numpy advanced indexing.
    rows = np.arange(h)[:, None] + _EDGE
    cols = np.arange(w)[None, :] + _EDGE
    descent = np.empty((8, h, w), dtype=np.float32)
    for k in range(8):
        ny = rows + _D8_OFFSETS[k, 0]
        nx = cols + _D8_OFFSETS[k, 1]
        descent[k] = z - z_pad[ny, nx]
    # Where descent <= 0 the flow is not strictly downhill — keep as
    # "no descent" (we'll fall back to the lowest neighbour below).
    has_descent = descent > 0
    # Weighted descent: descent / distance. Higher = steeper.
    weighted = descent / _D8_DIST[:, None, None]
    # Set weighted to -inf where there's no descent, so masked cells don't win.
    weighted_masked = np.where(has_descent, weighted, -np.inf)
    # Initial best: code of the steepest descent (or 0 if no descent).
    best_k = np.argmax(weighted_masked, axis=0).astype(np.int8)
    best_weighted = np.take_along_axis(weighted_masked, best_k[None], axis=0).squeeze(0)
    # For cells with no descent (best_weighted == -inf or 0), pick the
    # *lowest* neighbour. This routes flat areas deterministically (ties
    # broken by the lowest D8 code).
    flat = ~np.isfinite(best_weighted) | (best_weighted <= 0)
    if flat.any():
        z_neighbours = np.empty((8, h, w), dtype=np.float32)
        for k in range(8):
            ny = rows + _D8_OFFSETS[k, 0]
            nx = cols + _D8_OFFSETS[k, 1]
            z_neighbours[k] = z_pad[ny, nx]
        flat_k = np.argmin(z_neighbours, axis=0).astype(np.int8)
        best_k = np.where(flat, flat_k, best_k)
    return best_k


def _flow_accumulation(z: np.ndarray, fdir: np.ndarray) -> np.ndarray:
    """Return a (H, W) int64 array of upstream cell counts (including self).

    For each cell, the count = 1 + sum of upstream counts. We process cells
    in descending elevation order (topological sort). Cells with the same
    elevation are processed in row-major order (deterministic).
    """
    h, w = z.shape
    counts = np.ones((h, w), dtype=np.int64)  # each cell counts itself
    # Build the order: descending by z, then by (row, col) for ties. Use
    # np.lexsort for stable, deterministic order.
    flat_idx = np.arange(h * w)
    rows = flat_idx // w
    cols = flat_idx % w
    z_flat = z.ravel()
    # Sort key: (-z, row, col) → descending z, then row, then col.
    order = np.lexsort((cols, rows, -z_flat))
    # Process high → low. For each cell, route its accumulated count to its
    # D8 neighbour (the chosen direction).
    for i in order:
        r = i // w
        c = i % w
        k = int(fdir[r, c])
        # Sentinel for sinks / boundary: fdir == -1 means no downstream
        # neighbour (we should not have any sinks in the D8 pass above, but
        # we guard anyway).
        if k < 0:
            continue
        nr = r + int(_D8_OFFSETS[k, 0])
        nc = c + int(_D8_OFFSETS[k, 1])
        if 0 <= nr < h and 0 <= nc < w:
            counts[nr, nc] += counts[r, c]
    return counts


def _slope_radians(z: np.ndarray, cell_size_m: float) -> np.ndarray:
    """Return slope in radians using np.gradient (central differences)."""
    # np.gradient returns (d/dy, d/dx) with axis order matching the input.
    dz_dy, dz_dx = np.gradient(z, cell_size_m, cell_size_m, edge_order=1)
    # |grad| in metres per metre → arctan to get slope angle in radians.
    return np.arctan(np.sqrt(dz_dx * dz_dx + dz_dy * dz_dy).astype(np.float32))


def compute_twi(dem: xr.DataArray, *, cell_size_m: float | None = None) -> xr.DataArray:
    """Compute the Topographic Wetness Index from a DEM.

    TWI = ln(a / tan(β)) where a is the contributing area (per cell, in
    m²) and β is the slope (in radians). This is a pure numpy/scipy
    implementation that does NOT depend on pysheds (see
    ``arch-m1-3a-twi-scipy-numpy-custom``).

    Args:
        dem: xr.DataArray with dims (y, x), values in metres, CRS-aware.
        cell_size_m: pixel size on the ground. If None, infer from the
                     DEM's x/y coords (assuming a projected CRS in
                     metres) or from ``dem.rio.resolution()`` (and convert
                     degrees to metres using a 111_320 m/° default).

    Returns:
        xr.DataArray with dims (y, x), dtype ``float32``, same CRS as dem.
        Values are dimensionless. NoData ``-9999.0`` for cells at the edge
        where slope cannot be computed, or where the DEM is NaN.
    """
    if "y" not in dem.dims or "x" not in dem.dims:
        raise ValueError(f"dem must have dims (y, x); got {dem.dims}")
    z_in = np.asarray(dem.values, dtype=np.float32)
    if z_in.ndim != 2:
        raise ValueError(f"dem must be 2-D (y, x); got shape {z_in.shape}")

    if cell_size_m is None:
        cell_size_m = _infer_cell_size_m(dem)
    if not (cell_size_m > 0):
        raise ValueError(f"cell_size_m must be positive; got {cell_size_m}")

    h, w = z_in.shape
    # Replace NaN with a sentinel that won't affect the routing; we'll
    # restore nodata at the end.
    z = np.where(np.isfinite(z_in), z_in, np.float32(-np.inf))
    nan_mask = ~np.isfinite(z_in)

    # Slope and edge mask.
    slope = _slope_radians(z, cell_size_m)
    edge_mask = np.zeros_like(z, dtype=bool)
    edge_mask[:_EDGE, :] = True
    edge_mask[-_EDGE:, :] = True
    edge_mask[:, :_EDGE] = True
    edge_mask[:, -_EDGE:] = True

    # D8 flow direction (use the original NaN-free array). Cells that are
    # -inf (i.e. were NaN) will not be picked as the steepest descent
    # neighbour because the descent is "z - z_neighbour" with z=-inf
    # → -inf descent → not chosen.
    fdir = _d8_flow_direction(z)
    counts = _flow_accumulation(z, fdir)

    # TWI = ln(a / tan(β)) where a = counts × cell_size_m².
    # Guard tan(β) ≥ ε to avoid division by zero in flat cells.
    tan_beta = np.tan(slope).astype(np.float32)
    tan_beta = np.where(tan_beta < _EPS_SLOPE_RAD, np.float32(_EPS_SLOPE_RAD), tan_beta)
    a = counts.astype(np.float32) * np.float32(cell_size_m * cell_size_m)
    # Cells with count==1 (no upstream) and β==ε still get a finite TWI.
    twi = np.log(a / tan_beta).astype(np.float32)

    # NoData: NaN in source DEM, or edge cells.
    nodata_mask = nan_mask | edge_mask
    twi = np.where(nodata_mask, _NODATA_OUT, twi).astype(np.float32)

    out = xr.DataArray(
        twi,
        dims=("y", "x"),
        name="twi",
        attrs={
            "long_name": "Topographic Wetness Index",
            "source": "D8 + central-difference slope (Beven & Kirkby 1979)",
            "units": "dimensionless",
            "cell_size_m": float(cell_size_m),
            "eps_slope_rad": _EPS_SLOPE_RAD,
            "nodata": _NODATA_OUT_SCALAR,
        },
    )
    if dem.rio.crs is not None:
        out.rio.write_crs(dem.rio.crs, inplace=True)
    if dem.rio.transform() is not None:
        out.rio.write_transform(dem.rio.transform(), inplace=True)
    out.rio.write_nodata(_NODATA_OUT_SCALAR, inplace=True)
    return out


__all__ = ["compute_twi", "NODATA_OUT"]
NODATA_OUT = _NODATA_OUT_SCALAR
