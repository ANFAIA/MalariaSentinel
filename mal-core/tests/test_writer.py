"""Tests for the download writer module."""
import numpy as np
import pytest
import xarray as xr
import rioxarray  # noqa: F401 — registers .rio accessor
from pathlib import Path

from mal_core.download.writer import save_product


def test_save_dataarray_as_cog(tmp_path):
    da = xr.DataArray(
        np.random.rand(10, 10),
        dims=["y", "x"],
        attrs={"crs": "EPSG:4326"},
    )
    da = da.rio.set_spatial_dims(x_dim="x", y_dim="y")
    da = da.rio.write_crs("EPSG:4326")
    path = tmp_path / "test.tif"
    result = save_product(da, path)
    assert result.exists()
    assert result.suffix == ".tif"


def test_save_dataset_as_netcdf(tmp_path):
    ds = xr.Dataset({
        "temp": (["y", "x"], np.random.rand(10, 10)),
        "wind": (["y", "x"], np.random.rand(10, 10)),
    })
    path = tmp_path / "test.nc"
    result = save_product(ds, path)
    assert result.exists()
    assert result.suffix == ".nc"


# ── Phase 2: format parameter tests ────────────────────────────────────

def test_save_dataarray_as_netcdf_explicit(tmp_path):
    """format='nc' on a 2D DataArray should produce a NetCDF file."""
    da = xr.DataArray(
        np.random.rand(10, 10),
        dims=["y", "x"],
    )
    path = tmp_path / "explicit.nc"
    result = save_product(da, path, format="nc")
    assert result.exists()
    assert result.suffix == ".nc"
    # Verify it's readable as NetCDF
    loaded = xr.open_dataarray(str(result))
    assert loaded.shape == (10, 10)


def test_save_3d_dataarray_as_netcdf(tmp_path):
    """format='nc' on a 3D DataArray should produce a NetCDF file."""
    da = xr.DataArray(
        np.random.rand(12, 10, 10),
        dims=["time", "y", "x"],
    )
    path = tmp_path / "3d.nc"
    result = save_product(da, path, format="nc")
    assert result.exists()
    assert result.suffix == ".nc"
    loaded = xr.open_dataarray(str(result))
    assert loaded.shape == (12, 10, 10)


def test_save_3d_dataarray_tif_refuses(tmp_path):
    """format='tif' on a 3D DataArray should raise ValueError."""
    da = xr.DataArray(
        np.random.rand(12, 10, 10),
        dims=["time", "y", "x"],
    )
    path = tmp_path / "bad.tif"
    with pytest.raises(ValueError, match="3D DataArray requires NC writer"):
        save_product(da, path, format="tif")


def test_save_dataset_explicit_tif_refuses(tmp_path):
    """format='tif' on a Dataset should raise ValueError."""
    ds = xr.Dataset({"var": (["y", "x"], np.random.rand(10, 10))})
    path = tmp_path / "bad.tif"
    with pytest.raises(ValueError, match="Cannot write Dataset as TIF"):
        save_product(ds, path, format="tif")


def test_save_product_format_none_auto_detect(tmp_path):
    """format=None (default) should keep existing auto-detect behavior."""
    da = xr.DataArray(
        np.random.rand(10, 10),
        dims=["y", "x"],
        attrs={"crs": "EPSG:4326"},
    )
    da = da.rio.set_spatial_dims(x_dim="x", y_dim="y")
    da = da.rio.write_crs("EPSG:4326")
    path = tmp_path / "auto.tif"
    result = save_product(da, path, format=None)
    assert result.exists()
    assert result.suffix == ".tif"
