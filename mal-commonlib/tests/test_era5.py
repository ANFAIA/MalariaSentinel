"""Tests for ``mal_commonlib.data.loaders.era5`` (contract v3.0).

Covers:
    * ``load_era5_air_temp_daily`` — the daily-degree
      C channel: mocked CDS round-trip, °C conversion, reliable time axis,
      AOI-grid shape, nodata handling.
    * ``load_era5_wind_6hourly`` — month download/merge and auth error.
    * The annual-raster guard: nothing reads an annual TIF-like product as
      a daily series (plan 01 §7).
"""
from __future__ import annotations

import pathlib
from tempfile import mkdtemp

import numpy as np
import pytest
import xarray as xr

from mal_commonlib.aoi import AOI
from mal_commonlib.data.loaders import era5 as era5_mod
from mal_commonlib.data.loaders.era5 import (
    ERA5_NODATA,
    load_era5_air_temp_daily,
    load_era5_wind_6hourly,
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
        path = self._target if target is None else target
        ds = self._factory()
        # Written as NetCDF-3 classic: the venv has scipy.io.netcdf but not
        # netCDF4 / h5netcdf, so NETCDF4 would fail at write time.
        ds.to_netcdf(path, format="NETCDF3_CLASSIC")


def _make_era5_daily_K(
    aoi: AOI, *, centre_K: float = 298.15, half_range_K: float = 4.0,
    n_days: int = 3, h: int = 21, w: int = 21,
) -> xr.Dataset:
    """Synthetic ERA5-Land daily-statistics dataset: ``2m_temperature`` in
    K with a ``valid_time`` axis covering ``n_days`` July days, on a (h, w)
    grid covering the AOI bbox, varying smoothly with latitude."""
    west, south, east, north = aoi.bbox
    lons = np.linspace(west, east, w)
    lats = np.linspace(north, south, h)
    lon2d, lat2d = np.meshgrid(lons, lats)
    base = centre_K + half_range_K * (lat2d - 0.5 * (south + north)) / max(
        1e-6, 0.5 * (north - south)
    )
    t2m = np.stack(
        [base + float(d) for d in range(n_days)]  # +1 K per day
    ).astype(np.float32)
    times = np.array(
        [np.datetime64(f"2024-07-{d + 1:02d}") for d in range(n_days)]
    )
    return xr.Dataset(
        data_vars={"2m_temperature": (("valid_time", "y", "x"), t2m)},
        coords={"valid_time": times, "y": lats, "x": lons},
        attrs={"Conventions": "CF-1.6"},
    )


def _mock_cds_client(monkeypatch: pytest.MonkeyPatch, factory) -> None:
    """cdsapi-compatible client whose ``retrieve(name, request, target)``
    writes the synthetic NetCDF straight into ``target`` (cdsapi writes
    the payload at the supplied target path)."""

    def _make_mock_client():
        class _MockClient:
            def retrieve(self, name, request, target=None):
                if target is None:
                    raise AssertionError("loader should pass target=...")
                path = pathlib.Path(target)
                path.parent.mkdir(parents=True, exist_ok=True)
                factory().to_netcdf(path, format="NETCDF3_CLASSIC")
                return _MockCdsResult(str(path), factory)

        return _MockClient()

    import cdsapi

    monkeypatch.setattr(cdsapi, "Client", _make_mock_client)


# -- tests ------------------------------------------------------------------


def test_era5_requires_cds_auth(
    ghana_aoi: AOI, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In an env without CDS auth, the loader raises ``RuntimeError``."""
    import cdsapi

    def _raise_on_init(*_args, **_kwargs):
        raise RuntimeError("simulated missing CDS auth for test")

    monkeypatch.setattr(cdsapi, "Client", _raise_on_init)
    with pytest.raises(RuntimeError, match="CDS auth"):
        load_era5_air_temp_daily(ghana_aoi, years=[2024], months=[7])


def test_air_temp_daily_mock_roundtrip(
    ghana_aoi: AOI, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mocked CDS: (time, y, x) daily °C series on the AOI grid."""
    _mock_cds_client(
        monkeypatch,
        lambda: _make_era5_daily_K(ghana_aoi),
    )
    out = load_era5_air_temp_daily(
        ghana_aoi, years=[2024], months=[7], cache_dir=tmp_path / "era5-cache"
    )
    h, w = ghana_aoi.cells_per_side()
    assert out.dims == ("time", "y", "x")
    assert out.sizes["time"] == 3
    assert out.shape == (3, h, w)
    assert out.dtype == np.float32
    assert out.rio.crs is not None
    assert out.rio.crs.to_epsg() == 4326
    arr = out.values
    valid = arr[arr != ERA5_NODATA]
    assert valid.min() >= -50.0
    assert valid.max() <= 60.0
    # K→C: the 298.15 K centre maps to 25 °C (+1 K accumulates per day).
    assert 24.0 < float(valid.mean()) < 28.0
    # Real timestamps on the time axis (not a repeating annual stamp).
    assert str(out.time.values[0])[:10] == "2024-07-01"
    assert str(out.time.values[2])[:10] == "2024-07-03"
    assert out.attrs["aoi_slug"] == "ghana"
    assert out.attrs["nodata"] == ERA5_NODATA


def test_air_temp_daily_invalid_month_rejected(ghana_aoi: AOI) -> None:
    with pytest.raises(ValueError, match="month"):
        load_era5_air_temp_daily(ghana_aoi, years=[2024], months=[13])


def test_no_annual_raster_in_the_daily_contract(era5_module=era5_mod) -> None:
    """Plan 01 §7: the annual product keeps no daily alias, no raw daily
    read and no temp_suitability surface. Only the daily and wind loaders
    exist."""
    assert hasattr(era5_module, "load_era5_air_temp_daily")
    assert hasattr(era5_module, "load_era5_wind_6hourly")
    for retired in (
        "load_era5_temp_suitability",
        "sharpe_demichele_growth",
        "_monthly_mean_K_to_C",
        "T_OPT",
        "T_HALF_WIDTH",
    ):
        assert not hasattr(era5_module, retired), retired


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
    ghana_aoi: AOI, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock CDS client: retrieves the migration month and merges into a
    single NetCDF (retrieval writes straight into the requested target,
    as cdsapi does)."""
    import cdsapi

    calls: list[str] = []

    def _make_mock_client():
        class _MockClient:
            def retrieve(self, name, request, target=None):
                if target is None:
                    raise AssertionError("loader should pass target=...")
                month_list = request.get("month", [])
                calls.extend(month_list)
                ds = _make_wind_dataset(2024, 11, 2)
                path = pathlib.Path(target)
                path.parent.mkdir(parents=True, exist_ok=True)
                ds.to_netcdf(path, format="NETCDF3_CLASSIC")
                return _MockCdsResult(str(path), lambda: ds)

        return _MockClient()

    monkeypatch.setattr(cdsapi, "Client", _make_mock_client)
    out = load_era5_wind_6hourly(
        ghana_aoi, years=[2024], months=[11], cache_dir=tmp_path / "wind-cache"
    )
    assert calls, "expected at least one CDS retrieve call"
    assert "u100" in out.data_vars
    assert "v100" in out.data_vars


def test_load_era5_wind_6hourly_auth_error(
    ghana_aoi: AOI, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cdsapi

    def _raise_on_init(*_args, **_kwargs):
        raise RuntimeError("simulated missing CDS auth for test")

    monkeypatch.setattr(cdsapi, "Client", _raise_on_init)
    with pytest.raises(RuntimeError, match="CDS auth"):
        load_era5_wind_6hourly(
            ghana_aoi,
            years=[2024],
            months=[11],
            cache_dir=pathlib.Path(mkdtemp()) / "wind-cache",
        )


def test_load_era5_wind_6hourly_empty_years(ghana_aoi: AOI) -> None:
    with pytest.raises(ValueError, match="years"):
        load_era5_wind_6hourly(ghana_aoi, years=[])
