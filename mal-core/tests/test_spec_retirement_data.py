"""Checks migrated from the retired data specification.

The spec is gone; the facts live in the code and in this file. See
docs/plans/in-process/spec-retirement-ledger.md for the row that maps
each assertion to this test.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import mal_core.download.manifest as manifest_mod
from mal_core.download.manifest import (
    read_manifest,
    update_dataset,
    validate_completeness,
)

# The canonical on-disk naming (data/spec.md INV-1..INV-3).
TIME_SERIES_RE = re.compile(r"^[a-z0-9-]+_[a-z0-9_]+_\d{4}\.[a-z0-9]+$")
STATIC_RE = re.compile(r"^[a-z0-9-]+_[a-z0-9_]+\.[a-z0-9]+$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest_mod, "DATA_ROOT", tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# INV-1..INV-4: the file naming convention and the AOI slug
# ---------------------------------------------------------------------------

def test_slug_pattern_matches_the_conventional_aoi_names():
    assert SLUG_RE.match("ghana")
    assert SLUG_RE.match("accra-coastal")
    assert not SLUG_RE.match("Accra")
    assert not SLUG_RE.match("accra--coastal")


def test_time_series_and_static_names_follow_the_convention():
    assert TIME_SERIES_RE.match("ghana_wind_2024.nc")
    assert TIME_SERIES_RE.match("ghana_rainfall_2024.tif")
    assert STATIC_RE.match("ghana_population.tif")
    assert STATIC_RE.match("ghana_habitat_features.nc")
    assert not TIME_SERIES_RE.match("ghana_population.tif")
    # The static pattern is a superset of the time-series one: the spec's
    # own drift check accepted either ("ts.match(f) or st.match(f)").


def test_manifest_lives_at_data_aoi_manifest_json(data_root):
    (data_root / "ghana").mkdir()
    update_dataset("ghana", "wind", 2024, "ghana_wind_2024.nc", format="nc")
    assert (data_root / "ghana" / "manifest.json").exists()


# ---------------------------------------------------------------------------
# INV-5..INV-8: the manifest schema
# ---------------------------------------------------------------------------

def test_manifest_has_the_required_top_level_keys(data_root):
    (data_root / "ghana").mkdir()
    update_dataset("ghana", "wind", 2024, "ghana_wind_2024.nc", format="nc")
    manifest = read_manifest("ghana")
    for key in ("aoi", "datasets", "expected_files"):
        assert key in manifest, f"manifest is missing the top-level key {key!r}"
    assert manifest["aoi"] == "ghana"
    assert manifest["datasets"]["wind"]["files"]["2024"] == "ghana_wind_2024.nc"


def test_dataset_entry_schema(data_root):
    (data_root / "ghana").mkdir()
    update_dataset(
        "ghana", "chirps_rainfall_daily", None, "ghana_rainfall_daily.nc",
        type="time-series", required_for_abm=True, variables=["rainfall"],
        format="nc", period={"start": "2024-01-01", "end": "2024-12-31"},
    )
    entry = read_manifest("ghana")["datasets"]["chirps_rainfall_daily"]
    assert entry["type"] == "time-series"
    assert entry["format"] == "nc"
    assert entry["required_for_abm"] is True
    assert entry["variables"] == ["rainfall"]
    assert entry["period"] == {"start": "2024-01-01", "end": "2024-12-31"}
    assert entry["files"] == {"chirps_rainfall_daily": "ghana_rainfall_daily.nc"}


def test_expected_files_is_the_sorted_union_of_the_declared_files(data_root):
    (data_root / "ghana").mkdir()
    update_dataset("ghana", "wind", 2024, "ghana_wind_2024.nc", format="nc")
    update_dataset("ghana", "wind", 2025, "ghana_wind_2025.nc", format="nc")
    update_dataset("ghana", "population", None, "ghana_population.tif", format="tif")
    manifest = read_manifest("ghana")
    assert manifest["expected_files"] == sorted([
        "ghana_wind_2024.nc", "ghana_wind_2025.nc", "ghana_population.tif",
    ])


def test_a_missing_manifest_entry_means_not_available(data_root):
    """A dataset that was never registered does not exist for consumers."""
    from mal_core.download.manifest import resolve_dataset_file

    assert resolve_dataset_file("ghana", "host_static", data_root=data_root) is None
    assert read_manifest("ghana")["datasets"] == {}


def test_a_flat_v1_manifest_is_not_migrated_and_resolves_to_nothing(data_root):
    """The v1 flat "files" schema is gone: there is no migration path."""
    from mal_core.download.manifest import resolve_dataset_file

    aoi_dir = data_root / "ghana"
    aoi_dir.mkdir()
    (aoi_dir / "ghana_wind_2024.nc").write_text("dummy")
    (aoi_dir / "manifest.json").write_text(json.dumps({
        "aoi": "ghana",
        "files": {"2024": "ghana_wind_2024.nc"},
    }))

    manifest = read_manifest("ghana")
    # The flat block is not understood as a datasets block ...
    assert "datasets" not in manifest
    # ... and nothing is resolvable from it (no conventional-name fallback).
    assert resolve_dataset_file("ghana", "wind", data_root=data_root) is None
    assert validate_completeness("ghana", data_root=data_root) == []


def test_validate_completeness_reports_the_missing_files(data_root):
    (data_root / "ghana").mkdir()
    update_dataset("ghana", "wind", 2024, "ghana_wind_2024.nc", format="nc")
    assert validate_completeness("ghana", data_root=data_root) == ["ghana_wind_2024.nc"]
    (data_root / "ghana" / "ghana_wind_2024.nc").write_text("dummy")
    assert validate_completeness("ghana", data_root=data_root) == []


# ---------------------------------------------------------------------------
# INV-13 / INV-14: the loader contract (in memory, canonical signature)
# ---------------------------------------------------------------------------

def test_loaders_return_in_memory_objects_and_take_no_output_path():
    """The loaders return xr objects; the runner is the only save point."""
    import inspect

    from mal_core.download.registry import _loader_module_names
    import importlib

    seen = 0
    for mod_name in _loader_module_names():
        try:
            mod = importlib.import_module(f"mal_commonlib.data.loaders.{mod_name}")
        except Exception:
            continue
        dl = getattr(mod, "DOWNLOADER", None)
        if not dl:
            continue
        for out_name, func in dl["outputs"].items():
            seen += 1
            sig = inspect.signature(func)
            assert "output_path" not in sig.parameters
            assert "aoi" in sig.parameters
    assert seen > 0, "no loaders discovered"


def test_load_or_download_api_exists_on_the_public_loaders():
    """Every loader module exposes a public load_* function."""
    import importlib

    from mal_core.download.registry import _loader_module_names

    for mod_name in _loader_module_names():
        try:
            mod = importlib.import_module(f"mal_commonlib.data.loaders.{mod_name}")
        except Exception:
            continue
        if not getattr(mod, "DOWNLOADER", None):
            continue
        assert any(n.startswith("load_") for n in dir(mod)), (
            f"{mod_name}: no public load_* function")
