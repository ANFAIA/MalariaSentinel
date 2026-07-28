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

import calendar
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
    _monthly_mean_K_to_C,
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


def test_era5_requires_cds_auth(
    ghana_aoi: AOI, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In an env without CDS auth, the loader raises ``RuntimeError``.

    The check is made env-independent by monkeypatching ``cdsapi.Client``
    to raise on construction — simulating missing auth regardless of
    whether ``~/.cdsapirc`` is present in the developer's environment.
    """
    import cdsapi

    def _raise_on_init(*_args, **_kwargs):
        raise RuntimeError("simulated missing CDS auth for test")

    monkeypatch.setattr(cdsapi, "Client", _raise_on_init)
    with pytest.raises(RuntimeError, match="CDS auth"):
        load_era5_temp_suitability(ghana_aoi, year=2024, month=6)


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
        ghana_aoi, year=2024, month=6, cache_dir=tmp_path / "era5-cache"
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
        load_era5_temp_suitability(ghana_aoi, year=2024, month=13)


def test_monthly_mean_reduces_valid_time() -> None:
    """``_monthly_mean_K_to_C`` must reduce over the ``valid_time`` dim.

    The CDS ``derived-era5-land-daily-statistics`` dataset uses
    ``valid_time`` (not ``time``) for the daily-timestamps axis. Before the
    dim-name fix the function only reduced when ``"time" in da_K.dims``,
    so a (5, 4, 3) input came out (5, 4, 3) — the loader then failed the
    AOI-shape assertion downstream.
    """
    h, w = 4, 3
    n_days = 5
    # Constant K grid (300.15 K = 27.0 °C) broadcast over a time axis;
    # expected result is a (h, w) DataArray of 27.0 °C.
    t2m_K = np.full((n_days, h, w), 300.15, dtype=np.float32)
    da = xr.DataArray(t2m_K, dims=("valid_time", "y", "x"))
    out = _monthly_mean_K_to_C(da, 2024, 6)
    assert out.dims == ("y", "x")
    assert out.shape == (h, w)
    np.testing.assert_allclose(out.values, 27.0, atol=1e-4)
    assert out.dtype == np.float32


def test_monthly_mean_reduces_no_time_dim() -> None:
    """Regression: with no time-like dim, the function is a pure K→C cast.

    The per-month NetCDFs some ERA5 products ship have no leading time
    axis at all. The helper should convert and return the 2-D array
    unchanged in shape, not crash on the missing-dim path.
    """
    h, w = 4, 3
    t2m_K = np.full((h, w), 298.15, dtype=np.float32)
    da = xr.DataArray(t2m_K, dims=("y", "x"))
    out = _monthly_mean_K_to_C(da, 2024, 6)
    assert out.dims == ("y", "x")
    assert out.shape == (h, w)
    np.testing.assert_allclose(out.values, 25.0, atol=1e-4)
    assert out.dtype == np.float32


# -- ERA5 6-hourly wind download tests (M7.6 Phase 2) --


def _make_wind_dataset(year: int, month: int, n_days: int) -> xr.Dataset:
    """Build a synthetic ERA5 6-hourly wind dataset."""
    n_times = n_days * 4  # 4 slots per day
    times = np.arange(n_times, dtype=np.int64) * 6 * 3600  # 6-hourly offsets
    lats = np.linspace(11.5, 4.5, 29)
    lons = np.linspace(-3.5, 1.5, 21)
    u = np.random.default_rng(42).standard_normal((n_times, 29, 21)).astype(np.float32)
    v = np.random.default_rng(43).standard_normal((n_times, 29, 21)).astype(np.float32)
    return xr.Dataset(
        data_vars={"u100": (("valid_time", "latitude", "longitude"), u),
                    "v100": (("valid_time", "latitude", "longitude"), v)},
        coords={"valid_time": times, "latitude": lats, "longitude": lons},
    )


def test_load_era5_wind_6hourly_mock(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock CDS client: verifies load_era5_wind_6hourly calls CDS
    for each migration month and merges into a single NetCDF."""
    import cdsapi

    call_months: list[str] = []

    class _MockClient:
        def retrieve(self, name: str, request: dict, target: str | None = None) -> _MockCdsResult:
            assert target is not None
            month = request["month"][0]
            call_months.append(month)
            year = int(request["year"])
            m_int = int(month)
            n_days = calendar.monthrange(year, m_int)[1]
            pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
            _MockCdsResult(target, lambda: _make_wind_dataset(year, m_int, n_days)).download(target)
            return _MockCdsResult(target, lambda: _make_wind_dataset(year, m_int, n_days))

    monkeypatch.setattr(cdsapi, "Client", lambda: _MockClient())

    from mal_commonlib.data.loaders.era5 import load_era5_wind_6hourly, MIGRATION_SEASON_MONTHS

    out_path = str(tmp_path / "wind_6h_2024.nc")
    result = load_era5_wind_6hourly(
        "ghana", 2024,
        months=MIGRATION_SEASON_MONTHS[2024],
        output_path=out_path,
        cache_dir=tmp_path / "cache",
    )

    assert isinstance(result, xr.Dataset)
    assert "u100" in result.data_vars
    assert "v100" in result.data_vars
    # Migration months for 2024: Jul, Aug, Sep, Oct, Dec
    assert call_months == ["07", "08", "09", "10", "12"]
    # 5 months: 31+31+30+31+31 = 154 days × 4 slots = 616
    assert result.dims["valid_time"] == 616
    # Sorted by time
    assert (result.valid_time.diff("valid_time") >= 0).all()
    result.close()


def test_load_era5_wind_6hourly_full_year_mock(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full year download: all 12 months requested."""
    import cdsapi

    call_months: list[str] = []

    class _MockClient:
        def retrieve(self, name: str, request: dict, target: str | None = None) -> _MockCdsResult:
            assert target is not None
            month = request["month"][0]
            call_months.append(month)
            year = int(request["year"])
            m_int = int(month)
            n_days = calendar.monthrange(year, m_int)[1]
            pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
            _MockCdsResult(target, lambda: _make_wind_dataset(year, m_int, n_days)).download(target)
            return _MockCdsResult(target, lambda: _make_wind_dataset(year, m_int, n_days))

    monkeypatch.setattr(cdsapi, "Client", lambda: _MockClient())

    from mal_commonlib.data.loaders.era5 import load_era5_wind_6hourly

    out_path = str(tmp_path / "wind_6h_2024_full.nc")
    # months=None → all 12 months
    result = load_era5_wind_6hourly(
        "ghana", 2024,
        output_path=out_path,
        cache_dir=tmp_path / "cache",
    )

    assert isinstance(result, xr.Dataset)
    assert call_months == [f"{m:02d}" for m in range(1, 13)]
    assert result.dims["valid_time"] == 366 * 4  # 2024 is a leap year
    result.close()


def test_load_era5_wind_6hourly_auth_error(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing CDS auth raises RuntimeError."""
    import cdsapi

    def _raise(*_a, **_kw):
        raise RuntimeError("no auth")

    monkeypatch.setattr(cdsapi, "Client", _raise)

    from mal_commonlib.data.loaders.era5 import load_era5_wind_6hourly

    with pytest.raises(RuntimeError, match="CDS auth"):
        load_era5_wind_6hourly("ghana", 2024, output_path=str(tmp_path / "out.nc"))


def test_load_era5_wind_6hourly_empty_years() -> None:
    """Empty years list raises ValueError."""
    from mal_commonlib.data.loaders.era5 import load_era5_wind_6hourly

    with pytest.raises(ValueError, match="must not be empty"):
        load_era5_wind_6hourly("ghana", [], output_path="/tmp/out.nc")
