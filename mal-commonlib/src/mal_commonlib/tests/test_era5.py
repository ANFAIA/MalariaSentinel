"""Tests for ``mal_commonlib.data.loaders.era5`` (M1.3a).

Three tests:
    * ``test_era5_requires_cds_auth`` — calling the loader in an env without
      CDS auth raises ``RuntimeError`` with a clear "CDS auth" message. This
      is the M1.3a truth: CDS is not configured in this env.
    * ``test_sharpe_demichele_growth_known_values`` — pure-math tests of the
      growth response: 1.0 at T_OPT, 0.5 at T_OPT ± T_HALF_WIDTH/√2, 0.0 at
      the boundary of the viable range, 0.0 outside it.
    * ``test_era5_dry_run_no_network`` — monkeypatches
      ``cdsapi.Client().retrieve`` to write a synthetic ERA5-like NetCDF and
      asserts the loader returns temp_suitability in [0, 1] of the right
      shape, dtype float32, CRS = aoi.crs.
"""
from __future__ import annotations

import pathlib
from typing import Any

import numpy as np
import pytest
import xarray as xr

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders import era5 as era5_mod
from mal_commonlib.data.loaders.era5 import (
    ERA5_NODATA,
    T_HALF_WIDTH,
    T_OPT,
    load_era5_temp_suitability,
    sharpe_demichele_growth,
)


GHANA_W, GHANA_S, GHANA_E, GHANA_N = -1.0, 6.0, 0.0, 7.0


@pytest.fixture
def ghana_aoi() -> AOI:
    return AOI.from_bbox(
        GHANA_W, GHANA_S, GHANA_E, GHANA_N, "EPSG:4326", "ghana", 1000
    )


# -- helpers ----------------------------------------------------------------


class _MockCdsResult:
    """Stand-in for ``cdsapi.api.Result`` that writes a synthetic dataset
    to ``target`` on ``.download()``."""

    def __init__(self, target: str, factory) -> None:
        self._target = target
        self._factory = factory

    def download(self, target: str | None = None) -> None:
        # cdsapi calls download(self, target=None) — we ignore and write to
        # the target the loader asked for.
        path = self._target if target is None else target
        ds = self._factory()
        # Write as NetCDF-3 classic: the venv has scipy.io.netcdf but not
        # netCDF4 / h5netcdf, so NETCDF4 would fail at write time. NetCDF-3
        # round-trips through xarray's default engine fallback.
        ds.to_netcdf(path, format="NETCDF3_CLASSIC")


def _make_era5_dataset_K(
    aoi: AOI, *, centre_K: float = 298.15, half_range_K: float = 12.0,
    h: int = 21, w: int = 21,
) -> xr.Dataset:
    """Build a synthetic ERA5-Land-like dataset with ``2m_temperature`` in K
    on a (h, w) grid covering the AOI bbox, varying smoothly with latitude
    so different cells exercise different parts of the growth response.

    Written as NetCDF-3 (classic) because that's the only format the
    project venv can read without ``netCDF4`` or ``h5netcdf``."""
    west, south, east, north = aoi.bbox
    lons = np.linspace(west, east, w)
    lats = np.linspace(north, south, h)
    lon2d, lat2d = np.meshgrid(lons, lats)
    # Latitudinal gradient (~2 K/deg, equator → pole, just for shape).
    t2m = centre_K + half_range_K * (lat2d - 0.5 * (south + north)) / max(
        1e-6, 0.5 * (north - south)
    )
    t2m = t2m.astype(np.float32)
    return xr.Dataset(
        data_vars={
            "2m_temperature": (("y", "x"), t2m),
        },
        coords={"y": lats, "x": lons},
        attrs={"Conventions": "CF-1.6"},
    )


# -- tests ------------------------------------------------------------------


def test_era5_requires_cds_auth(ghana_aoi: AOI) -> None:
    """In an env without CDS auth, the loader raises ``RuntimeError``."""
    # Make sure no CDS env vars / config leak in. cdsapi.Client() reads
    # ~/.cdsapirc and CDSAPI_URL/KEY; we just call the loader and expect it
    # to detect the missing auth and raise.
    with pytest.raises(RuntimeError, match="CDS auth"):
        load_era5_temp_suitability(ghana_aoi, 2024, 6)


def test_sharpe_demichele_growth_known_values() -> None:
    """Pure-math tests of the growth response shape."""
    T = xr.DataArray(
        [
            T_OPT,                                  # → 1.0
            T_OPT + T_HALF_WIDTH / np.sqrt(2),      # → 0.5
            T_OPT - T_HALF_WIDTH / np.sqrt(2),      # → 0.5
            T_OPT + T_HALF_WIDTH,                   # → 0.0  (boundary)
            T_OPT - T_HALF_WIDTH,                   # → 0.0  (boundary)
            T_OPT + T_HALF_WIDTH + 5.0,             # → 0.0  (outside)
            T_OPT - T_HALF_WIDTH - 5.0,             # → 0.0  (outside)
        ],
        dims=("t",),
    )
    s = sharpe_demichele_growth(T)
    expected = np.array([1.0, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(s.values, expected, atol=1e-6)


def test_sharpe_demichele_growth_dtype_and_shape() -> None:
    """The helper must preserve shape and return float32."""
    t = xr.DataArray(np.linspace(0, 40, 50).reshape(5, 10), dims=("y", "x"))
    s = sharpe_demichele_growth(t)
    assert s.shape == (5, 10)
    assert s.dtype == np.float32
    # Within the viable range, the function is positive; outside, 0.
    centre = s.sel(y=2, x=5).item()
    assert 0.0 < centre <= 1.0


def test_era5_dry_run_no_network(
    ghana_aoi: AOI, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a monkeypatched CDS client, the loader returns a (H, W)
    temp_suitability in [0, 1] of the right shape and dtype."""
    import cdsapi

    def _make_mock_client():
        def _factory() -> xr.Dataset:
            return _make_era5_dataset_K(ghana_aoi)

        class _MockClient:
            def retrieve(self, name: str, request: dict, target: str | None = None) -> _MockCdsResult:
                # The loader passes target=str(cache_dir / file.nc). We must
                # create the file at that path so xr.open_dataset can read it.
                if target is None:
                    raise AssertionError("loader should pass target=...")
                # Make sure parent dir exists; the loader creates it but we
                # are defensive.
                import pathlib as _p

                _p.Path(target).parent.mkdir(parents=True, exist_ok=True)
                return _MockCdsResult(target, _factory)

        return _MockClient()

    monkeypatch.setattr(cdsapi, "Client", _make_mock_client)

    out = load_era5_temp_suitability(
        ghana_aoi, 2024, 6, cache_dir=tmp_path / "era5-cache"
    )

    h, w = ghana_aoi.cells_per_side()
    assert out.shape == (h, w)
    assert out.dtype == np.float32
    # CRS round-trips.
    assert out.rio.crs is not None
    assert out.rio.crs.to_epsg() == 4326
    # All real values (not -9999) in [0, 1].
    arr = out.values
    valid = arr != ERA5_NODATA
    if valid.any():
        v = arr[valid]
        assert v.min() >= 0.0
        assert v.max() <= 1.0
    # Attrs are recorded for the env writer sidecar.
    assert out.attrs["aoi_slug"] == "ghana"
    assert out.attrs["year"] == 2024
    assert out.attrs["month"] == 6
    assert out.attrs["nodata"] == ERA5_NODATA
    # Dims are exactly (y, x).
    assert out.dims == ("y", "x")


def test_era5_invalid_month_rejected(ghana_aoi: AOI) -> None:
    # The month check runs before the CDS auth check, so out-of-range
    # months surface as ValueError. In-range months without CDS auth
    # surface as RuntimeError (see ``test_era5_requires_cds_auth``).
    with pytest.raises(ValueError, match="month"):
        load_era5_temp_suitability(ghana_aoi, 2024, 13)
