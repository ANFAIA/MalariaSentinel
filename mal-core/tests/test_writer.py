"""Tests for the download writer module."""
import numpy as np
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
