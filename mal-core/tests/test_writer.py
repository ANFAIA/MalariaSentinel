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


# --- M13 Phase 2: format param + 3D guard tests ---


def test_save_dataarray_3d_as_netcdf(tmp_path):
    """3D DataArray saved as NC when format='nc'."""
    da = xr.DataArray(
        np.random.rand(5, 10, 10),
        dims=["time", "y", "x"],
        attrs={"crs": "EPSG:4326"},
    )
    da = da.rio.set_spatial_dims(x_dim="x", y_dim="y")
    da = da.rio.write_crs("EPSG:4326")
    path = tmp_path / "test_3d.nc"
    result = save_product(da, path, format="nc")
    assert result.exists()
    assert result.suffix == ".nc"
    # Verify it's a valid NC that xarray can read
    ds = xr.open_dataset(path)
    assert "time" in ds.dims


def test_save_dataarray_3d_as_tif_raises(tmp_path):
    """3D DataArray raises ValueError when format='tif'."""
    da = xr.DataArray(
        np.random.rand(5, 10, 10),
        dims=["time", "y", "x"],
    )
    path = tmp_path / "test_3d.tif"
    with pytest.raises(ValueError, match="3D DataArray"):
        save_product(da, path, format="tif")


def test_save_product_format_hint(tmp_path):
    """format='nc' forces NC output even for 2D DataArray."""
    da = xr.DataArray(
        np.random.rand(10, 10),
        dims=["y", "x"],
        attrs={"crs": "EPSG:4326"},
    )
    da = da.rio.set_spatial_dims(x_dim="x", y_dim="y")
    da = da.rio.write_crs("EPSG:4326")
    path = tmp_path / "test_hint.nc"
    result = save_product(da, path, format="nc")
    assert result.suffix == ".nc"
    # Verify it's a valid NC
    ds = xr.open_dataset(path)
    assert len(ds.data_vars) > 0


def test_save_product_unknown_format_raises(tmp_path):
    """Unknown format string raises ValueError."""
    da = xr.DataArray(np.random.rand(5, 5), dims=["y", "x"])
    path = tmp_path / "test.bin"
    with pytest.raises(ValueError, match="Unknown format"):
        save_product(da, path, format="csv")


def test_save_dataarray_2d_default_tif(tmp_path):
    """Default (format=None) for 2D DataArray still produces TIF."""
    da = xr.DataArray(
        np.random.rand(10, 10),
        dims=["y", "x"],
        attrs={"crs": "EPSG:4326"},
    )
    da = da.rio.set_spatial_dims(x_dim="x", y_dim="y")
    da = da.rio.write_crs("EPSG:4326")
    path = tmp_path / "test_default.tif"
    result = save_product(da, path)
    assert result.suffix == ".tif"


def test_save_dataset_default_nc(tmp_path):
    """Default (format=None) for Dataset still produces NC."""
    ds = xr.Dataset({"var": (["y", "x"], np.random.rand(10, 10))})
    path = tmp_path / "test_default.nc"
    result = save_product(ds, path)
    assert result.suffix == ".nc"
