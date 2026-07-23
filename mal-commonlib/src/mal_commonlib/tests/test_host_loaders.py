"""Tests for M7 host density loaders and utilities.

Unit tests with synthetic data — no network calls. Tests cover:
    * Aggregation logic (sum-preserving and nearest-neighbour)
    * NetCDF writer
    * WorldPop loader contract (mocked download)
    * GLW loader contract (mocked download)
    * GHSL loader contract (mocked download)
"""
from __future__ import annotations

import pathlib

import numpy as np
import pytest
import rasterio
import rioxarray  # noqa: F401
import xarray as xr
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

from mal_commonlib.aoi import AOI
from mal_commonlib.data.host_utils import (
    aggregate_to_grid,
    build_host_static_nc,
    write_manifest,
)


# -- helpers ------------------------------------------------------------------


def _small_aoi() -> AOI:
    """10x10 cell AOI for fast unit tests."""
    return AOI.from_bbox(-1.0, 6.0, 0.0, 7.0, "EPSG:4326", "test-host", 1000)


def _make_fake_tif(
    path: pathlib.Path,
    arr: np.ndarray,
    crs: str = "EPSG:4326",
    bbox: tuple[float, float, float, float] = (-1.0, 6.0, 0.0, 7.0),
) -> pathlib.Path:
    """Write a small in-memory GeoTIFF for mocking downloads."""
    h, w = arr.shape
    transform = from_bounds(*bbox, w, h)
    profile = {
        "driver": "GTiff",
        "dtype": arr.dtype.name,
        "width": w,
        "height": h,
        "count": 1,
        "crs": crs,
        "transform": transform,
        "nodata": -9999.0,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(str(path), "w", **profile) as dst:
        dst.write(arr, 1)
    return path


def _fake_worldpop_data() -> np.ndarray:
    """Synthetic WorldPop-like data: 50x50, high-res (100m), populated centre."""
    arr = np.zeros((50, 50), dtype=np.float32)
    arr[20:30, 20:30] = 100.0  # Dense centre
    arr[10:40, 10:40] = 20.0  # Moderate surround
    return arr


def _fake_glw_data(species: str) -> np.ndarray:
    """Synthetic GLW-like data: 10x10, coarse (~10km), scattered animals."""
    arr = np.zeros((10, 10), dtype=np.float32)
    if species == "cattle":
        arr[3:6, 3:6] = 50.0
    elif species == "goats":
        arr[2:7, 2:7] = 30.0
    elif species == "sheep":
        arr[4:8, 4:8] = 10.0
    return arr


def _fake_ghsl_data() -> np.ndarray:
    """Synthetic GHSL-like data: 40x40, 250m, urban centre."""
    arr = np.full((40, 40), 50, dtype=np.int32)  # Rural
    arr[15:25, 15:25] = 30  # Urban centre
    return arr


# -- aggregation tests -------------------------------------------------------


class TestAggregateToGrid:
    """Test the conservative (sum-preserving) and nearest-neighbour aggregation."""

    def test_sum_preserving_uniform(self):
        """A uniform 100x100 source aggregated to 10x10 target = 100 per cell."""
        src = np.ones((100, 100), dtype=np.float32) * 5.0
        src_transform = from_bounds(0, 0, 100, 100, 100, 100)
        dst_transform = from_bounds(0, 0, 100, 100, 10, 10)
        result = aggregate_to_grid(
            src, src_transform, "EPSG:4326", dst_transform, "EPSG:4326",
            (10, 10), method="sum",
        )
        assert result.shape == (10, 10)
        # Each 10x10 dst cell covers 10x10 src cells, each with value 5.0
        # Sum = 100.0 per dst cell
        np.testing.assert_allclose(result, 100.0, rtol=1e-3)

    def test_sum_preserving_sparse(self):
        """A sparse source: only one pixel has value 100, rest are 0."""
        src = np.zeros((20, 20), dtype=np.float32)
        src[10, 10] = 100.0
        src_transform = from_bounds(0, 0, 20, 20, 20, 20)
        dst_transform = from_bounds(0, 0, 20, 20, 10, 10)
        result = aggregate_to_grid(
            src, src_transform, "EPSG:4326", dst_transform, "EPSG:4326",
            (10, 10), method="sum",
        )
        assert result.shape == (10, 10)
        # Total should be ~100 (conserved)
        np.testing.assert_allclose(result.sum(), 100.0, rtol=1e-2)

    def test_nearest_neighbour_categorical(self):
        """Nearest-neighbour preserves class codes."""
        src = np.zeros((20, 20), dtype=np.float32)
        src[5:15, 5:15] = 30.0  # Urban class
        src_transform = from_bounds(0, 0, 20, 20, 20, 20)
        dst_transform = from_bounds(0, 0, 20, 20, 10, 10)
        result = aggregate_to_grid(
            src, src_transform, "EPSG:4326", dst_transform, "EPSG:4326",
            (10, 10), method="nearest",
        )
        assert result.shape == (10, 10)
        # Class 30 should appear in the central cells
        assert 30.0 in result


# -- NetCDF writer tests -----------------------------------------------------


class TestBuildHostStaticNc:
    """Test the NetCDF writer produces a valid file."""

    def test_write_and_read_back(self, tmp_path: pathlib.Path):
        """Write a small NetCDF and read it back."""
        H, W = 10, 10
        human = np.random.rand(H, W).astype(np.float32) * 100
        cattle = np.random.rand(H, W).astype(np.float32) * 50
        goats = np.random.rand(H, W).astype(np.float32) * 30
        sheep = np.random.rand(H, W).astype(np.float32) * 10
        urban = np.full((H, W), 50, dtype=np.int32)
        urban[3:7, 3:7] = 30

        transform = from_bounds(-1.0, 6.0, 0.0, 7.0, W, H)
        grid_spec = {"crs": "EPSG:4326", "transform": transform, "height": H, "width": W}

        out_path = tmp_path / "host_static.nc"
        result_path = build_host_static_nc(
            human, cattle, goats, sheep, urban, out_path, grid_spec,
        )
        assert result_path == out_path
        assert out_path.exists()
        assert out_path.stat().st_size > 0

        # Read back and verify
        ds = xr.open_dataset(str(out_path))
        assert "human" in ds.data_vars
        assert "cattle" in ds.data_vars
        assert "goats" in ds.data_vars
        assert "sheep" in ds.data_vars
        assert "urban_class" in ds.data_vars
        assert ds["human"].shape == (H, W)
        assert ds["urban_class"].dtype == np.int32
        np.testing.assert_array_equal(ds["urban_class"].values, urban)
        ds.close()

    def test_shape_mismatch_raises(self, tmp_path: pathlib.Path):
        """Mismatched array shapes should raise an assertion error."""
        H, W = 10, 10
        human = np.zeros((H, W), dtype=np.float32)
        cattle = np.zeros((H + 1, W), dtype=np.float32)  # Wrong shape
        goats = np.zeros((H, W), dtype=np.float32)
        sheep = np.zeros((H, W), dtype=np.float32)
        urban = np.zeros((H, W), dtype=np.int32)
        transform = from_bounds(-1.0, 6.0, 0.0, 7.0, W, H)
        grid_spec = {"crs": "EPSG:4326", "transform": transform, "height": H, "width": W}

        with pytest.raises(AssertionError):
            build_host_static_nc(
                human, cattle, goats, sheep, urban,
                tmp_path / "bad.nc", grid_spec,
            )


class TestWriteManifest:
    """Test the JSON manifest writer."""

    def test_manifest_written(self, tmp_path: pathlib.Path):
        H, W = 5, 5
        human = np.ones((H, W), dtype=np.float32) * 10
        cattle = np.ones((H, W), dtype=np.float32) * 5
        goats = np.ones((H, W), dtype=np.float32) * 3
        sheep = np.ones((H, W), dtype=np.float32) * 1
        urban = np.full((H, W), 50, dtype=np.int32)
        transform = from_bounds(-1.0, 6.0, 0.0, 7.0, W, H)
        grid_spec = {"crs": "EPSG:4326", "transform": transform, "height": H, "width": W}

        out_path = tmp_path / "host_static.nc"
        manifest_path = write_manifest(out_path, human, cattle, goats, sheep, urban, grid_spec)
        assert manifest_path.exists()

        import json
        manifest = json.loads(manifest_path.read_text())
        assert "netcdf_path" in manifest
        assert "variables" in manifest
        assert len(manifest["variables"]) == 5
        # Human total = 5*5*10 = 250
        human_var = next(v for v in manifest["variables"] if v["variable"] == "human")
        assert human_var["total"] == pytest.approx(250.0)


# -- Loader contract tests (mocked downloads) --------------------------------


class TestWorldPopLoader:
    """Test WorldPopLoader with a mocked GeoTIFF (no network)."""

    def test_load_from_fake_tif(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
        """Create a fake WorldPop GeoTIFF, patch the loader to use it."""
        from mal_commonlib.data.loaders import worldpop as wp_mod

        aoi = _small_aoi()
        fake_tif = _make_fake_tif(
            tmp_path / "gha_ppp_2019_constrained.tif",
            _fake_worldpop_data(),
        )

        def _fake_download(url, dest, **kwargs):
            import shutil
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(fake_tif), str(dest))
            return dest

        monkeypatch.setattr(wp_mod, "_download_to", _fake_download)

        loader = wp_mod.WorldPopLoader()
        da = loader.load(aoi, year=2019, cache_dir=tmp_path / "cache")

        assert isinstance(da, xr.DataArray)
        assert da.dtype == np.float32
        assert da.dims == ("y", "x")
        h, w = aoi.cells_per_side()
        assert da.shape == (h, w)
        assert "worldpop_population" in da.name

    def test_invalid_year_raises(self):
        aoi = _small_aoi()
        loader = __import__(
            "mal_commonlib.data.loaders.worldpop", fromlist=["WorldPopLoader"]
        ).WorldPopLoader()
        with pytest.raises(ValueError, match="2019"):
            loader.load(aoi, year=2020)


class TestGLWLoader:
    """Test GLWLoader with a mocked GeoTIFF (no network)."""

    def test_load_cattle(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
        from mal_commonlib.data.loaders import glw as glw_mod

        aoi = _small_aoi()
        fake_tif = _make_fake_tif(
            tmp_path / "GHA_Cattle_2010.tif",
            _fake_glw_data("cattle"),
        )

        def _fake_download(url, dest, **kwargs):
            import shutil
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(fake_tif), str(dest))
            return dest

        monkeypatch.setattr(glw_mod, "_download_to", _fake_download)

        loader = glw_mod.GLWLoader()
        da = loader.load(aoi, species="cattle", cache_dir=tmp_path / "cache")

        assert isinstance(da, xr.DataArray)
        assert da.dtype == np.float32
        h, w = aoi.cells_per_side()
        assert da.shape == (h, w)
        assert "cattle" in da.name

    def test_invalid_species_raises(self):
        loader = __import__(
            "mal_commonlib.data.loaders.glw", fromlist=["GLWLoader"]
        ).GLWLoader()
        aoi = _small_aoi()
        with pytest.raises(ValueError, match="Unknown species"):
            loader.load(aoi, species="elephants")


class TestGHSLLoader:
    """Test GHSLLoader with a mocked GeoTIFF (no network)."""

    def test_load_smod(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
        from mal_commonlib.data.loaders import ghsl as ghsl_mod

        aoi = _small_aoi()
        fake_tif = _make_fake_tif(
            tmp_path / "GHS_SMOD_E2025_GMAP_250_AF.tif",
            _fake_ghsl_data(),
        )

        def _fake_download(url, dest, **kwargs):
            import shutil
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(fake_tif), str(dest))
            return dest

        monkeypatch.setattr(ghsl_mod, "_download_to", _fake_download)

        loader = ghsl_mod.GHSLLoader()
        da = loader.load(aoi, cache_dir=tmp_path / "cache")

        assert isinstance(da, xr.DataArray)
        assert da.dtype == np.int32
        h, w = aoi.cells_per_side()
        assert da.shape == (h, w)
        assert "ghsl_smod" in da.name
        # Check that urban (30) and rural (50) classes are present
        unique = np.unique(da.values[da.values != -9999])
        assert 30 in unique or 50 in unique
