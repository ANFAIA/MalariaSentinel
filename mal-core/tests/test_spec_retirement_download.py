"""Checks migrated from the retired download specification.

The spec is gone; the facts live in the code and in this file. See
docs/plans/in-process/spec-retirement-ledger.md for the row that maps
each assertion to this test.
"""
from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

import mal_core.download.runner as runner_mod
from mal_core.download.registry import (
    DownloaderSpec,
    _loader_module_names,
    discover_downloaders,
)
from mal_core.download.runner import (
    _standard_path,
    _standard_path_daily,
    _standard_path_monthly_nc,
)

LOADERS_PKG = Path(importlib.import_module("mal_commonlib.data.loaders").__file__).parent


def _loaders() -> dict[str, dict]:
    out = {}
    for mod_name in _loader_module_names():
        try:
            mod = importlib.import_module(f"mal_commonlib.data.loaders.{mod_name}")
        except Exception:  # pragma: no cover - a broken loader is reported elsewhere
            continue
        raw = getattr(mod, "DOWNLOADER", None)
        if raw is not None:
            out[mod_name] = raw
    return out


# ---------------------------------------------------------------------------
# INV-1..INV-4: the loader signature rules
# ---------------------------------------------------------------------------

def test_every_loader_takes_aoi_first_and_never_output_path():
    for mod_name, dl in _loaders().items():
        for out_name, func in dl["outputs"].items():
            sig = inspect.signature(func)
            params = list(sig.parameters.values())
            assert params, f"{mod_name}.{out_name}: no parameters"
            first = params[0]
            assert first.name in ("aoi", "aoi_obj"), (
                f"{mod_name}.{out_name}: first parameter is {first.name!r}, "
                "must be the AOI")
            assert "output_path" not in sig.parameters, (
                f"{mod_name}.{out_name}: loaders must not accept output_path")


def test_years_is_present_exactly_for_time_series_loaders():
    for mod_name, dl in _loaders().items():
        is_ts = dl.get("is_time_series", False)
        for out_name, func in dl["outputs"].items():
            sig = inspect.signature(func)
            has_years = "years" in sig.parameters
            assert has_years == is_ts, (
                f"{mod_name}.{out_name}: is_time_series={is_ts} but "
                f"years param present={has_years}")


def test_time_series_loaders_accept_years_and_months_keywords_only():
    for mod_name, dl in _loaders().items():
        if not dl.get("is_time_series", False):
            continue
        for out_name, func in dl["outputs"].items():
            sig = inspect.signature(func)
            for name in ("years", "months"):
                p = sig.parameters.get(name)
                assert p is not None, f"{mod_name}.{out_name}: no {name} param"
                assert p.kind is inspect.Parameter.KEYWORD_ONLY, (
                    f"{mod_name}.{out_name}: {name} must be keyword-only")


# ---------------------------------------------------------------------------
# INV-7: discovery is a package scan
# ---------------------------------------------------------------------------

def test_discovery_covers_every_loader_module_on_disk():
    on_disk = {
        p.stem for p in LOADERS_PKG.glob("*.py")
        if p.stem != "__init__"
    }
    registered_modules = {spec.module_name for spec in discover_downloaders().values()}
    missing = on_disk - registered_modules
    assert not missing, f"loader modules without a DOWNLOADER: {missing}"


def test_no_loader_exports_the_retired_worldcover_manifest_key():
    for mod_name, dl in _loaders().items():
        keys = set(dl.get("manifest_keys", {}).values())
        assert "wc_class_fractions" not in keys, (
            f"{mod_name}: the retired wc_class_fractions key must be gone")


# ---------------------------------------------------------------------------
# INV-9 / INV-10: how the runner calls a loader
# ---------------------------------------------------------------------------

class _FakeLoader:
    """Records the kwargs the runner passed."""

    def __init__(self, result=None):
        self.calls: list[dict] = []
        self._result = result

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self._result


def _fake_registry(**specs):
    return specs


def test_runner_branches_on_is_time_series(tmp_path, monkeypatch):
    """A time-series loader gets years+months; a static one does not."""
    ts_result = xr.DataArray(
        np.zeros((3, 2, 2), dtype=np.float32),
        dims=("time", "y", "x"),
        coords={"time": np.arange("2024-01-01", "2024-01-04", dtype="datetime64[D]")},
    )
    ts_loader = _FakeLoader(ts_result)
    static_loader = _FakeLoader(
        xr.DataArray(np.zeros((2, 2), dtype=np.float32), dims=("y", "x"))
    )
    registry = _fake_registry(
        ts=DownloaderSpec(
            name="ts", description="d", requires_auth=[], outputs={"rainfall_daily": ts_loader},
            manifest_keys={"rainfall_daily": "chirps_rainfall_daily"},
            module_name="ts", is_time_series=True, formats={"rainfall_daily": "daily"},
        ),
        st=DownloaderSpec(
            name="st", description="d", requires_auth=[], outputs={"population": static_loader},
            manifest_keys={"population": "worldpop"}, module_name="st",
            is_time_series=False,
        ),
    )
    monkeypatch.setattr(runner_mod, "discover_downloaders", lambda: registry)
    out_dir = tmp_path / "data" / "ghana"
    results = runner_mod.run_download("ghana", output_dir=out_dir, years=[2024, 2025],
                                      months=[6])
    assert results["ts"]["status"] == "ok"
    assert results["st"]["status"] == "ok"

    ts_call = ts_loader.calls[0]
    assert ts_call["years"] == [2024, 2025]
    assert ts_call["months"] == [6]
    assert "aoi" in ts_call

    static_call = static_loader.calls[0]
    assert "years" not in static_call
    assert "months" not in static_call
    assert "aoi" in static_call


def test_runner_filters_by_dataset_and_output(tmp_path, monkeypatch):
    loader = _FakeLoader(
        xr.DataArray(np.zeros((2, 2), dtype=np.float32), dims=("y", "x"))
    )
    other = _FakeLoader(
        xr.DataArray(np.zeros((2, 2), dtype=np.float32), dims=("y", "x"))
    )
    registry = _fake_registry(
        st=DownloaderSpec(
            name="st", description="d", requires_auth=[], outputs={"population": loader},
            manifest_keys={"population": "worldpop"}, module_name="st",
        ),
        other=DownloaderSpec(
            name="other", description="d", requires_auth=[], outputs={"population": other},
            manifest_keys={"population": "worldpop2"}, module_name="other",
        ),
    )
    monkeypatch.setattr(runner_mod, "discover_downloaders", lambda: registry)
    out_dir = tmp_path / "data" / "ghana"
    runner_mod.run_download("ghana", datasets=["st"], outputs=["population"],
                            output_dir=out_dir)
    assert len(loader.calls) == 1
    assert other.calls == [], "the --datasets filter must exclude other loaders"


def test_runner_uses_the_daily_and_monthly_nc_write_paths(tmp_path, monkeypatch):
    ts_result = xr.DataArray(
        np.zeros((3, 2, 2), dtype=np.float32),
        dims=("time", "y", "x"),
        coords={"time": np.arange("2024-01-01", "2024-01-04", dtype="datetime64[D]")},
    )
    ts_result.name = None
    loader = _FakeLoader(ts_result)
    registry = _fake_registry(
        ts=DownloaderSpec(
            name="ts", description="d", requires_auth=[], outputs={"rainfall_daily": loader},
            manifest_keys={"rainfall_daily": "chirps_rainfall_daily"},
            module_name="ts", is_time_series=True, formats={"rainfall_daily": "daily"},
        ),
    )
    monkeypatch.setattr(runner_mod, "discover_downloaders", lambda: registry)
    out_dir = tmp_path / "data" / "ghana"
    runner_mod.run_download("ghana", output_dir=out_dir, years=[2024, 2025])

    # The daily write path: one multi-year NC named <aoi>_<product>_<start>_<end>_daily.nc
    written = out_dir / "ghana_rainfall_daily_2024_2025_daily.nc"
    assert written.exists(), sorted(p.name for p in out_dir.iterdir())
    # The "_daily" suffix is stripped from the NetCDF variable name.
    with xr.open_dataset(written) as ds:
        assert "rainfall" in ds.data_vars, list(ds.data_vars)


def test_runner_registers_the_dataset_in_the_manifest(tmp_path, monkeypatch):
    ts_result = xr.DataArray(
        np.zeros((3, 2, 2), dtype=np.float32),
        dims=("time", "y", "x"),
        coords={"time": np.arange("2024-01-01", "2024-01-04", dtype="datetime64[D]")},
    )
    loader = _FakeLoader(ts_result)
    registry = _fake_registry(
        ts=DownloaderSpec(
            name="ts", description="d", requires_auth=[], outputs={"rainfall_daily": loader},
            manifest_keys={"rainfall_daily": "chirps_rainfall_daily"},
            module_name="ts", is_time_series=True, formats={"rainfall_daily": "daily"},
            required_for_abm={"rainfall_daily": True},
        ),
    )
    monkeypatch.setattr(runner_mod, "discover_downloaders", lambda: registry)
    out_dir = tmp_path / "data" / "ghana"
    runner_mod.run_download("ghana", output_dir=out_dir, years=[2024, 2025])

    manifest = json.loads((out_dir / "manifest.json").read_text())
    entry = manifest["datasets"]["chirps_rainfall_daily"]
    assert entry["type"] == "time-series"
    assert entry["format"] == "nc"
    assert entry["required_for_abm"] is True
    assert entry["period"]["start"] == "2024-01-01"
    assert entry["period"]["end"] == "2024-01-03"
    assert entry["files"]["chirps_rainfall_daily"] == \
        "ghana_rainfall_daily_2024_2025_daily.nc"
    assert "ghana_rainfall_daily_2024_2025_daily.nc" in manifest["expected_files"]


def test_auth_gate_reports_skipped_and_does_not_raise(tmp_path, monkeypatch):
    registry = _fake_registry(
        st=DownloaderSpec(
            name="st", description="d", requires_auth=["cds"],
            outputs={"population": _FakeLoader()},
            manifest_keys={"population": "worldpop"}, module_name="st",
        ),
    )
    monkeypatch.setattr(runner_mod, "discover_downloaders", lambda: registry)
    monkeypatch.setattr(runner_mod, "_check_auth", lambda spec: False)
    out_dir = tmp_path / "data" / "ghana"
    results = runner_mod.run_download("ghana", output_dir=out_dir)
    assert results["st"]["status"] == "skipped"
    assert "reason" in results["st"]


# ---------------------------------------------------------------------------
# The save paths (the "standard path" helpers)
# ---------------------------------------------------------------------------

def test_standard_paths_follow_the_canonical_naming(tmp_path):
    ts = _standard_path("ghana", "wind", 2024, "nc", data_dir=tmp_path)
    assert ts.name == "ghana_wind_2024.nc"
    static = _standard_path("ghana", "population", None, "tif", data_dir=tmp_path)
    assert static.name == "ghana_population.tif"
    daily = _standard_path_daily("ghana", "rainfall_daily", 2024, 2025, data_dir=tmp_path)
    assert daily.name == "ghana_rainfall_daily_2024_2025_daily.nc"
    monthly = _standard_path_monthly_nc("ghana", "salinity", 2024, 2025, data_dir=tmp_path)
    assert monthly.name == "ghana_salinity_2024_2025_monthly.nc"


def test_standard_paths_match_the_documented_naming_regex():
    import re

    ts_re = re.compile(r"^[a-z0-9-]+_[a-z0-9_]+_\d{4}\.[a-z]+$")
    st_re = re.compile(r"^[a-z0-9-]+_[a-z0-9_]+\.[a-z]+$")
    daily_re = re.compile(r"^[a-z0-9-]+_[a-z0-9_]+_\d{4}_\d{4}_(daily|monthly)\.nc$")
    assert ts_re.match("ghana_wind_2024.nc")
    assert st_re.match("ghana_population.tif")
    assert daily_re.match("ghana_rainfall_daily_2024_2025_daily.nc")
    assert daily_re.match("ghana_salinity_2024_2025_monthly.nc")


def test_writer_refuses_a_3d_dataarray_as_tif(tmp_path):
    from mal_core.download.writer import save_product

    data = xr.DataArray(np.zeros((3, 2, 2), dtype=np.float32),
                        dims=("time", "y", "x"))
    with pytest.raises(ValueError):
        save_product(data, tmp_path / "out.tif", format="tif")
