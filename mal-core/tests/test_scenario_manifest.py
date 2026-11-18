"""Scenario definitions travel in the manifest as ``scenario:<id>`` keys.

Covers the Paso 0 plumbing: the manifest key is validated like any other
dataset, a scenario is resolved by its id only (never "the first one"), an
undeclared scenario is an explicit error, and ``--scenario`` reaches the C++
binary as a ``--scenario <path>`` flag. The engine itself is never executed.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mal_core.download.catalog import (
    SCENARIO_ARTIFACT,
    catalog_status,
    declared_scenarios,
    resolve,
    resolve_scenario,
    scenario_key,
)
from mal_core.download.manifest import validate_completeness

AOI = "synth-test"


def _write_manifest(root: Path, datasets: dict) -> Path:
    d = root / AOI
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(
        json.dumps({"aoi": AOI, "datasets": datasets, "expected_files": []}),
        encoding="utf-8",
    )
    return d


def _base_datasets(scenarios: tuple[str, ...] = ("E01",)) -> dict:
    """Minimal manifest: env + habitat (required by the ABM) plus scenarios."""
    datasets: dict = {
        "env": {"type": "time-series", "files": {"2024": "env_2024.nc"}},
        "habitat": {"type": "static", "files": {"habitat": "habitat.gpkg"}},
    }
    for sid in scenarios:
        datasets[scenario_key(sid)] = {
            "type": "static",
            "format": "json",
            "required_for_abm": False,
            "files": {sid: f"scenarios/{sid}.json"},
        }
    return datasets


def _populate(d: Path, scenarios: tuple[str, ...] = ("E01",)) -> None:
    (d / "env_2024.nc").write_bytes(b"nc")
    (d / "habitat.gpkg").write_bytes(b"gpkg")
    (d / "scenarios").mkdir(exist_ok=True)
    for sid in scenarios:
        (d / "scenarios" / f"{sid}.json").write_text(
            json.dumps({"id": sid}), encoding="utf-8"
        )


@pytest.fixture
def root(tmp_path: Path) -> Path:
    r = tmp_path / "data"
    d = _write_manifest(r, _base_datasets(("E01", "E02")))
    _populate(d, ("E01", "E02"))
    return r


# --- manifest validation and resolution -------------------------------------

def test_scenario_key_is_validated_by_completeness(root):
    assert validate_completeness(AOI, data_root=root) == []


def test_missing_scenario_file_is_reported_as_incomplete(root):
    (root / AOI / "scenarios" / "E02.json").unlink()
    missing = validate_completeness(AOI, data_root=root)
    assert "scenarios/E02.json" in missing


def test_resolve_returns_the_scenario_path(root):
    path = resolve(AOI, "scenario:E01", data_root=root)
    assert path == root / AOI / "scenarios" / "E01.json"


def test_resolve_returns_none_without_the_key(tmp_path):
    r = tmp_path / "data"
    d = _write_manifest(r, _base_datasets(scenarios=()))
    _populate(d, scenarios=())
    assert resolve(AOI, "scenario:E01", data_root=r) is None


def test_resolve_scenario_picks_the_requested_id_not_the_first(root):
    assert declared_scenarios(AOI, data_root=root) == ["E01", "E02"]
    assert resolve_scenario(AOI, "E02", data_root=root) == (
        root / AOI / "scenarios" / "E02.json"
    )


def test_undeclared_scenario_is_an_explicit_error(tmp_path):
    r = tmp_path / "data"
    d = _write_manifest(r, _base_datasets(scenarios=("E01",)))
    _populate(d, scenarios=("E01", "E07"))
    with pytest.raises(FileNotFoundError, match="E07.*not declared.*Declared scenarios: E01"):
        resolve_scenario(AOI, "E07", data_root=r)


def test_declared_scenario_without_file_entry_is_an_error(tmp_path):
    r = tmp_path / "data"
    datasets = _base_datasets(scenarios=())
    datasets[scenario_key("E01")] = {"type": "static", "files": {"other": "x.json"}}
    d = _write_manifest(r, datasets)
    _populate(d, scenarios=())
    with pytest.raises(FileNotFoundError, match="does not declare files\\['E01'\\]"):
        resolve_scenario(AOI, "E01", data_root=r)


def test_invalid_scenario_id_is_rejected(root):
    with pytest.raises(ValueError, match="invalid scenario id"):
        resolve_scenario(AOI, "../E01", data_root=root)


def test_catalog_status_lists_declared_scenarios_only(root):
    rows = [r for r in catalog_status(AOI, data_root=root) if r["kind"] == "scenario"]
    assert [r["key"] for r in rows] == ["scenario:E01", "scenario:E02"]
    assert all(r["in_manifest"] and r["on_disk"] for r in rows)
    assert all(r["required_for_abm"] is False for r in rows)
    # The bare artifact name is never a manifest key of its own.
    assert SCENARIO_ARTIFACT.key == "scenario"
    assert not any(r["key"] == "scenario" for r in catalog_status(AOI, data_root=root))


# --- --scenario reaches the binary --------------------------------------------

def _run_from_manifest(root: Path, monkeypatch, scenario):
    """Run the production path with a fake binary; return the argv it built."""
    from mal_core.abm import wrapper

    argv: list[list[str]] = []

    def fake_subprocess_run(cmd, **_kwargs):
        argv.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(wrapper.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(
        wrapper.CppAbmWrapper, "_resolve_binary", lambda self: Path("/fake/mal_abm_fast")
    )
    result = wrapper.run_abm_from_manifest(
        aoi=AOI,
        days=1,
        output_dir=root.parent / "runs",
        data_root=root,
        scenario=scenario,
    )
    assert result["returncode"] == 0
    run_cmds = [c for c in argv if c[1:2] == ["run"]]
    assert len(run_cmds) == 1
    return run_cmds[0]


def test_scenario_flag_reaches_the_binary_command(root, monkeypatch):
    cmd = _run_from_manifest(root, monkeypatch, scenario="E02")
    i = cmd.index("--scenario")
    assert cmd[i + 1] == str(root / AOI / "scenarios" / "E02.json")


def test_no_scenario_means_no_scenario_flag(root, monkeypatch):
    cmd = _run_from_manifest(root, monkeypatch, scenario=None)
    assert "--scenario" not in cmd


def test_undeclared_scenario_never_runs_the_binary(tmp_path, monkeypatch):
    from mal_core.abm import wrapper

    r = tmp_path / "data"
    d = _write_manifest(r, _base_datasets(scenarios=()))
    _populate(d, scenarios=())

    def boom(*_a, **_k):  # pragma: no cover - must not be reached
        raise AssertionError("the binary must not run for an undeclared scenario")

    monkeypatch.setattr(wrapper.subprocess, "run", boom)
    monkeypatch.setattr(
        wrapper.CppAbmWrapper, "_resolve_binary", lambda self: Path("/fake/mal_abm_fast")
    )
    with pytest.raises(FileNotFoundError, match="E01.*not declared"):
        wrapper.run_abm_from_manifest(
            aoi=AOI, days=1, output_dir=tmp_path / "runs", data_root=r, scenario="E01",
        )


def test_cli_scenario_and_data_root_reach_the_wrapper(monkeypatch, tmp_path):
    import mal_core.abm as abm_pkg
    from mal_core.cli import app

    captured: dict = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(abm_pkg, "run_abm_from_manifest", fake)
    result = CliRunner().invoke(
        app,
        ["abm", "--aoi", AOI, "--days", "1", "--scenario", "E01",
         "--data-root", str(tmp_path / "data")],
    )
    assert result.exit_code == 0, result.output
    assert captured["scenario"] == "E01"
    assert captured["data_root"] == tmp_path / "data"


# --- the producer's dynamics code matches the engine's contract ----------------

def test_dynamics_codes_cover_every_habitat_label():
    from mal_core.habitat.config import dynamics_map
    from mal_core.ingest.env import DYNAMICS_CODE

    assert set(DYNAMICS_CODE.values()) == {0, 1}
    assert set(DYNAMICS_CODE) == set(dynamics_map().values())
