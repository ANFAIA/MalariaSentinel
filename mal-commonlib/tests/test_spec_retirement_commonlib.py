"""Checks migrated from the retired commonlib specification.

The spec is gone; the facts live in the code and in this file. See
docs/plans/in-process/spec-retirement-ledger.md for the row that maps
each assertion to this test.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from rasterio.transform import from_bounds

COMMONLIB_SRC = Path(__file__).resolve().parents[1] / "src" / "mal_commonlib"


# ---------------------------------------------------------------------------
# INV-7: the repo paths
# ---------------------------------------------------------------------------

def test_runs_dir_exists_after_import():
    from mal_commonlib.config import RUNS_DIR

    assert RUNS_DIR.exists()
    assert RUNS_DIR.is_dir()


def test_the_repo_paths_are_repo_relative():
    from mal_commonlib.config import (
        DATA_DIR,
        PAPERS_DIR,
        REPO_ROOT,
        RUNS_DIR,
        TERRAIN_DIR,
    )

    for path in (DATA_DIR, PAPERS_DIR, REPO_ROOT, RUNS_DIR, TERRAIN_DIR):
        assert path.is_absolute()
        assert path.exists(), f"{path} does not exist"


# ---------------------------------------------------------------------------
# INV-8: the static host NetCDF
# ---------------------------------------------------------------------------

def _host_nc(path, h=4, w=4):
    from mal_commonlib.data.host_utils import build_host_static_nc

    grid_spec = {
        "crs": "EPSG:32630",
        "transform": from_bounds(0, 0, 1000, 1000, w, h),
        "height": h,
        "width": w,
    }
    ones = np.ones((h, w), dtype=np.float32)
    build_host_static_nc(
        human=ones, cattle=ones, goats=ones, sheep=ones,
        urban_class=np.full((h, w), 50, dtype=np.int32),
        output_path=path, grid_spec=grid_spec,
        pigs=ones, chickens=ones,
        building_fraction=np.full((h, w), 0.5, dtype=np.float32),
        wildlife_host_proxy=np.full((h, w), 0.3, dtype=np.float32),
    )
    return path


def test_the_host_static_nc_is_cf18_with_a_crs_coordinate_variable(tmp_path):
    path = _host_nc(tmp_path / "ghana_host_static.nc")
    with xr.open_dataset(path) as ds:
        assert ds.attrs.get("Conventions") == "CF-1.8"
        assert "crs" in ds.coords or "crs" in ds.variables
        assert "crs_wkt" in ds["crs"].attrs
        assert ds["human"].dims == ("y", "x")
        assert ds["human"].dtype == np.float32
        assert ds["urban_class"].dtype == np.int32


def test_the_host_static_nc_carries_the_nine_documented_variables(tmp_path):
    path = _host_nc(tmp_path / "ghana_host_static.nc")
    with xr.open_dataset(path) as ds:
        for var in ("human", "cattle", "goats", "sheep", "pigs", "chickens",
                    "urban_class", "building_fraction", "wildlife_host_proxy"):
            assert var in ds.data_vars, f"missing the {var!r} variable"


def test_the_host_manifest_companion_is_written(tmp_path):
    from mal_commonlib.data.host_utils import write_manifest

    out_dir = tmp_path / "hosts"
    out_dir.mkdir()
    path = out_dir / "ghana_host_static.nc"
    ones = np.ones((4, 4), dtype=np.float32)
    write_manifest(
        path, ones, ones, ones, ones,
        np.full((4, 4), 50, dtype=np.int32),
        {"crs": "EPSG:32630", "transform": from_bounds(0, 0, 1000, 1000, 4, 4),
         "height": 4, "width": 4},
    )
    manifest_path = out_dir / "host_manifest.json"
    assert manifest_path.exists()
    payload = json.loads(manifest_path.read_text())
    assert payload


# ---------------------------------------------------------------------------
# INV-9: the CSR binary layout (C++ SparseOD::load_from_csr)
# ---------------------------------------------------------------------------

def test_the_csr_binary_layout_matches_the_cpp_reader(tmp_path):
    from mal_commonlib.data.mobility import build_gravity_od, write_csr

    grid = np.arange(16, dtype=np.float32).reshape(4, 4) + 1.0
    row_ptr, col_idx, values, n_rows, n_cols = build_gravity_od(grid, 1.0, 0.5)
    path = write_csr(row_ptr, col_idx, values, n_rows, n_cols,
                     tmp_path / "mobility.csr")
    raw = path.read_bytes()
    n_rows_r = np.frombuffer(raw, dtype="<i4", count=1, offset=0)[0]
    n_cols_r = np.frombuffer(raw, dtype="<i4", count=1, offset=4)[0]
    nnz = np.frombuffer(raw, dtype="<i4", count=1, offset=8)[0]
    assert n_rows_r == n_rows
    assert n_cols_r == n_cols
    assert nnz == col_idx.shape[0]
    # [int32 x (n_rows+1)] row_ptr, then [int32 x nnz] col_idx, then float32 values
    assert len(raw) == 12 + 4 * (n_rows + 1) + 4 * nnz + 4 * nnz


# ---------------------------------------------------------------------------
# The AOI JSON payload
# ---------------------------------------------------------------------------

def test_aoi_to_file_writes_the_documented_keys(tmp_path):
    from mal_commonlib.aoi import AOI

    aoi = AOI.from_slug("ghana")
    path = aoi.to_file(tmp_path / "aoi.json")
    payload = json.loads(path.read_text())
    for key in ("slug", "name", "bbox", "crs", "resolution_m", "scale",
                "gadm_id"):
        assert key in payload, f"the AOI JSON is missing {key!r}"
    assert payload["slug"] == "ghana"
    assert payload["bbox"] == list(aoi.bbox)


# ---------------------------------------------------------------------------
# The retired terrain layer (TWI / DEM) must stay retired
# ---------------------------------------------------------------------------

def test_the_twi_terrain_module_is_gone():
    assert not (COMMONLIB_SRC / "terrain").exists()
    with pytest.raises(ModuleNotFoundError):
        import mal_commonlib.terrain.twi  # noqa: F401


def test_the_dem_loader_is_gone():
    loader_dir = COMMONLIB_SRC / "data" / "loaders"
    assert not (loader_dir / "dem.py").exists()


def test_k_max_is_not_a_configured_constant():
    """K_MAX was retired with state contract 4.0 (2026-10-20)."""
    import mal_commonlib.config as config_mod

    assert not hasattr(config_mod, "K_MAX")
